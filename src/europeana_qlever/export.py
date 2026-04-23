"""Export SPARQL results from QLever to TSV and convert to Parquet.

Phase 1 streams SPARQL TSV results to disk via httpx, then parses RDF
terms with rdflib and writes Parquet with PyArrow.  Phase 2 uses DuckDB
to compose final exports from raw Parquet tables (values_*, links_*).

Composable exports:

- ``links`` tables are Hive-partitioned directories. Each declared link
  property becomes one SPARQL scan written directly to
  ``{exports_dir}/<table>/x_property=<col>/data.parquet``. Readers see
  the directory as a single logical table with DuckDB's
  ``hive_partitioning=true``.
- ``merged``, ``group``, and ``map`` exports are built by DuckDB
  composition from raw Parquets.
"""

from __future__ import annotations

import itertools
import logging
import math
import os
import time
from datetime import datetime
from collections import deque
from collections.abc import Callable
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import nullcontext
from functools import partial
from pathlib import Path

import duckdb
import httpx
import pyarrow as pa
import pyarrow.parquet as pq
from rdflib.util import from_n3
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.text import Text

from . import display
from .constants import (
    DEFAULT_EXPORT_MAX_RETRIES,
    DEFAULT_EXPORT_RETRY_DELAYS,
    QLEVER_PORT,
    QLEVER_QUERY_TIMEOUT,
)
from .compose import (
    ComposeStep,
    chunked_compose_steps_for,
    compose_steps_for,
    merged_items_chunk_sql,
    merged_items_prepare_specs,
)
from .schema_loader import (
    depends_on as _deps_for,
    export_classes,
    export_sets as _schema_export_sets,
    links_scan_entries,
)
from .query import Query, QueryFilters, QueryRegistry
from .state import ExportResult

logger = logging.getLogger(__name__)

# Suppress rdflib.term warnings about technically-invalid IRIs.
logging.getLogger("rdflib.term").setLevel(logging.ERROR)


# ---------------------------------------------------------------------------
# Export type hierarchy
# ---------------------------------------------------------------------------


from dataclasses import dataclass, field


@dataclass
class Export:
    """Base class for anything that produces a Parquet file (or Parquet set)."""

    name: str
    description: str = ""
    depends_on: list[str] = field(default_factory=list)


@dataclass
class QueryExport(Export):
    """Exports a SPARQL query result to Parquet (Phase 1).

    For an ordinary ``values_*`` or composite-base query the output is a
    single ``<name>.parquet`` file. For per-property links scans
    (``partition_of`` set) the output goes to the parent links table's
    Hive partition: ``<parent>/x_property=<column>/data.parquet``.
    """

    sparql: str = ""
    partition_of: str | None = None   # parent links table, if this is a partition scan
    partition_column: str | None = None  # e.g. "v_dc_subject"

    @classmethod
    def from_query(
        cls,
        query: Query,
        filters: QueryFilters | None = None,
        *,
        partition_of: str | None = None,
        partition_column: str | None = None,
    ) -> QueryExport:
        return cls(
            name=query.name,
            description=query.description,
            sparql=query.sparql(filters),
            partition_of=partition_of,
            partition_column=partition_column,
        )


@dataclass
class CompositeExport(Export):
    """Composes Parquet files via DuckDB (Phase 2).

    If ``compose_steps`` is empty, the export is a pure dependency
    aggregator (used for Hive-partitioned links tables that are just a
    directory of per-property scans).
    """

    compose_steps: list[ComposeStep] = field(default_factory=list)


# ---------------------------------------------------------------------------
# ExportSet
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExportSet:
    """A named collection of exports.  Exports can belong to multiple sets."""

    name: str
    description: str
    members: tuple[str, ...]

    def resolve(self, registry: dict[str, Export]) -> dict[str, Export]:
        return {n: registry[n] for n in self.members if n in registry}


_SET_DESCRIPTIONS: dict[str, str] = {
    "pipeline": "All 30 final exports: raw + merged + group + maps",
    "raw": "Raw values_* and links_* tables — one row per EDM entity (values) or one row per value (links)",
    "merged": "Flagship denormalized merged_items table",
    "group": "Fast-analytics group_items table with only categorical/boolean/integer columns",
    "maps": "Static lookup and navigation tables: map_rights, map_sameAs, map_cho_entities",
}


def _build_export_sets() -> dict[str, ExportSet]:
    schema_sets = _schema_export_sets()
    result: dict[str, ExportSet] = {}
    for name, members in schema_sets.items():
        result[name] = ExportSet(
            name=name,
            description=_SET_DESCRIPTIONS.get(name, f"{name} exports"),
            members=tuple(members),
        )
    return result


EXPORT_SETS: dict[str, ExportSet] = _build_export_sets()


# ---------------------------------------------------------------------------
# ExportRegistry
# ---------------------------------------------------------------------------


class ExportRegistry:
    """Builds exports from the query registry and composite definitions."""

    def __init__(self, filters: QueryFilters | None = None) -> None:
        self._query_registry = QueryRegistry()
        self._filters = filters
        self._exports: dict[str, Export] = self._build()

    @property
    def query_registry(self) -> QueryRegistry:
        return self._query_registry

    @property
    def exports(self) -> dict[str, Export]:
        return dict(self._exports)

    def get(self, name: str) -> Export:
        return self._exports[name]

    def for_set(self, set_name: str) -> dict[str, Export]:
        if set_name == "all":
            return self.exports
        es = EXPORT_SETS[set_name]
        return {n: self._exports[n] for n in es.members if n in self._exports}

    def for_names(self, names: list[str]) -> dict[str, Export]:
        result: dict[str, Export] = {}
        for n in names:
            if n not in self._exports:
                raise KeyError(f"Unknown export: {n!r}")
            result[n] = self._exports[n]
        return result

    def _build(self) -> dict[str, Export]:
        exports: dict[str, Export] = {}
        scan_entries = links_scan_entries()

        # 1. values_* tables — one QueryExport each.
        for info in export_classes().values():
            if info.export_type == "values":
                q = self._query_registry.get(info.table_name)
                exports[info.table_name] = QueryExport.from_query(q, self._filters)

        # 2. Per-property links scans — one QueryExport per partition.
        for scan_name, entry in scan_entries.items():
            q = self._query_registry.get(scan_name)
            exports[scan_name] = QueryExport.from_query(
                q,
                self._filters,
                partition_of=entry.parent_table,
                partition_column=entry.property_column,
            )

        # 3. links tables — Hive-partitioned directory, represented as a
        #    no-op CompositeExport whose only job is to depend on every
        #    per-property scan for that table.
        parent_scans: dict[str, list[str]] = {}
        for scan_name, entry in scan_entries.items():
            parent_scans.setdefault(entry.parent_table, []).append(scan_name)
        for info in export_classes().values():
            if info.export_type != "links":
                continue
            deps = sorted(parent_scans.get(info.table_name, []))
            exports[info.table_name] = CompositeExport(
                name=info.table_name,
                description=f"{info.cls_name}: Hive-partitioned links (by x_property)",
                compose_steps=[],
                depends_on=deps,
            )

        # 4. merged_items / group_items / map_* — declared depends_on.
        for info in export_classes().values():
            if info.export_type in ("merged", "group", "map"):
                exports[info.table_name] = CompositeExport(
                    name=info.table_name,
                    description=info.annotations.get("description", info.cls_name),
                    compose_steps=compose_steps_for(info.table_name),
                    depends_on=_deps_for(info.table_name),
                )

        return exports


# ---------------------------------------------------------------------------
# Streaming SPARQL to TSV
# ---------------------------------------------------------------------------


_TRANSIENT_STATUS_CODES = {429, 502, 503, 504}


class _RowSpeedColumn(ProgressColumn):
    def render(self, task: Task) -> Text:
        speed = task.speed
        if speed is None:
            return Text("? rows/s", style="progress.data.speed")
        return Text(f"{speed:,.0f} rows/s", style="progress.data.speed")


def _cleanup_partial(*paths: Path) -> None:
    for p in paths:
        try:
            if p.exists():
                p.unlink()
                logger.info("Removed partial file: %s", p)
        except OSError:
            pass


def _stream_query(
    query: str,
    output_path: Path,
    qlever_url: str,
    timeout: int,
    *,
    http_chunk_size: int = 1_048_576,
    http_connect_timeout: int = 30,
    on_chunk: "Callable[[int], None] | None" = None,
) -> int:
    """Stream a SPARQL TSV result to disk.

    If ``on_chunk`` is provided, the caller drives progress reporting and
    no internal UI is rendered. Otherwise an ephemeral Rich Progress bar
    is shown for the duration of the stream.
    """
    total_bytes = 0
    newlines = 0

    progress: Progress | None = None
    task = None
    if on_chunk is None:
        columns: list[ProgressColumn] = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            DownloadColumn(),
        ]
        if not display.is_narrow():
            columns.append(TransferSpeedColumn())
        columns.append(TimeElapsedColumn())

        desc = output_path.stem
        if display.is_narrow() and len(desc) > 15:
            desc = desc[:14] + "…"

        progress = Progress(*columns, console=display.console)
        progress.start()
        task = progress.add_task(f"→ {desc}", total=None)

    try:
        with httpx.stream(
            "POST",
            qlever_url,
            data={"query": query, "action": "tsv_export", "timeout": f"{timeout}s"},
            timeout=httpx.Timeout(timeout + 120, connect=http_connect_timeout),
        ) as response:
            if response.status_code != 200:
                error_body = response.read().decode("utf-8", errors="replace")[:2000]
                display.console.print(
                    f"[red]QLever export failed ({response.status_code}):[/red]"
                )
                display.console.print(error_body)
                response.raise_for_status()

            with open(output_path, "wb") as fh:
                for chunk in response.iter_bytes(chunk_size=http_chunk_size):
                    fh.write(chunk)
                    total_bytes += len(chunk)
                    newlines += chunk.count(b"\n")
                    if progress is not None:
                        progress.update(task, completed=total_bytes)
                    if on_chunk is not None:
                        on_chunk(len(chunk))
    finally:
        if progress is not None:
            progress.stop()

    return max(0, newlines - 1)


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TransportError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _TRANSIENT_STATUS_CODES
    return False


def run_query_to_tsv(
    query: str,
    output_path: Path,
    qlever_url: str = f"http://localhost:{QLEVER_PORT}",
    timeout: int = QLEVER_QUERY_TIMEOUT,
    *,
    max_retries: int = DEFAULT_EXPORT_MAX_RETRIES,
    retry_delays: tuple[int, ...] = DEFAULT_EXPORT_RETRY_DELAYS,
    http_chunk_size: int = 1_048_576,
    http_connect_timeout: int = 30,
    on_chunk: "Callable[[int], None] | None" = None,
) -> int:
    """Stream a SPARQL query result from QLever directly to a TSV file."""
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return _stream_query(
                query, output_path, qlever_url, timeout,
                http_chunk_size=http_chunk_size,
                http_connect_timeout=http_connect_timeout,
                on_chunk=on_chunk,
            )
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries and _is_transient(exc):
                delay = retry_delays[attempt] if attempt < len(retry_delays) else retry_delays[-1]
                logger.warning(
                    "Query to %s failed (attempt %d/%d): %s. Retrying in %ds",
                    output_path.name,
                    attempt + 1,
                    max_retries + 1,
                    exc,
                    delay,
                )
                _cleanup_partial(output_path)
                time.sleep(delay)
            else:
                raise
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TSV → Parquet
# ---------------------------------------------------------------------------


PARQUET_BATCH_SIZE = 100_000


def parse_rdf_term(raw: str) -> str:
    """Parse a SPARQL TSV cell from N-Triples syntax to a clean string."""
    if not raw:
        return ""
    first = raw[0]
    if first == '"' or first == "<" or raw.startswith("_:"):
        try:
            term = from_n3(raw)
        except Exception:
            return raw.strip('"<>').split('"')[0]
        if term is None:
            return ""
        return str(term)
    return raw


def _parse_batch(raw_lines: list[str], num_cols: int) -> list[list[str]]:
    rows = []
    for line in raw_lines:
        cells = line.rstrip("\n").split("\t")
        if len(cells) < num_cols:
            cells.extend([""] * (num_cols - len(cells)))
        elif len(cells) > num_cols:
            cells = cells[:num_cols]
        rows.append([parse_rdf_term(c) for c in cells])
    return rows


def _read_raw_batches(fh, batch_size: int) -> list[str]:
    batch: list[str] = []
    for line in fh:
        batch.append(line)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _infer_schema(col_names: list[str], sample_rows: list[list[str]]) -> pa.Schema:
    fields = []
    for i, name in enumerate(col_names):
        vals = [row[i] for row in sample_rows if i < len(row) and row[i]]
        if vals and all(v.lstrip("-").isdigit() for v in vals):
            fields.append(pa.field(name, pa.int64()))
        elif vals and all(_is_float(v) for v in vals):
            fields.append(pa.field(name, pa.float64()))
        elif vals and all(v in ("true", "false") for v in vals):
            fields.append(pa.field(name, pa.bool_()))
        else:
            fields.append(pa.field(name, pa.string()))
    return pa.schema(fields)


def _is_float(v: str) -> bool:
    try:
        float(v)
        return "." in v
    except ValueError:
        return False


def _make_array(values: tuple, field: pa.Field) -> pa.Array:
    if field.type == pa.int64():
        return pa.array([int(v) if v else None for v in values], type=pa.int64())
    if field.type == pa.float64():
        return pa.array([float(v) if v else None for v in values], type=pa.float64())
    if field.type == pa.bool_():
        return pa.array([v == "true" if v else None for v in values], type=pa.bool_())
    if pa.types.is_timestamp(field.type):
        return pa.array(
            [_parse_timestamp(v) if v else None for v in values],
            type=field.type,
        )
    return pa.array([v if v else None for v in values], type=pa.string())


def _parse_timestamp(v: str) -> datetime | None:
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _write_batch(writer: pq.ParquetWriter, schema: pa.Schema, rows: list[list[str]]) -> None:
    columns = list(zip(*rows)) if rows else []
    arrays = [_make_array(columns[i], field) for i, field in enumerate(schema)]
    batch = pa.RecordBatch.from_arrays(arrays, schema=schema)
    writer.write_batch(batch)


def tsv_to_parquet(
    tsv_path: Path,
    parquet_path: Path,
    *,
    batch_size: int = PARQUET_BATCH_SIZE,
    row_group_size: int = 100_000,
    workers: int | None = None,
    total_hint: int | None = None,
    static_schema: pa.Schema | None = None,
    show_progress: bool = True,
    on_rows: "Callable[[int], None] | None" = None,
) -> int:
    """Parse a SPARQL TSV file with rdflib and write Parquet with PyArrow.

    If ``on_rows`` is provided, the caller drives progress reporting and
    no internal UI is rendered (``show_progress`` is implicitly False).
    """
    if workers is None:
        workers = max(1, (os.cpu_count() or 4) // 2)

    with open(tsv_path, "r", encoding="utf-8") as fh:
        header = fh.readline().strip()
        if not header:
            return 0
        col_names = [c.lstrip("?") for c in header.split("\t")]
        num_cols = len(col_names)

        total_rows = 0
        parse = partial(_parse_batch, num_cols=num_cols)
        writer: pq.ParquetWriter | None = None
        schema: pa.Schema | None = None

        desc = tsv_path.stem
        if display.is_narrow() and len(desc) > 15:
            desc = desc[:14] + "…"

        prog_cols: list[ProgressColumn] = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ]
        if total_hint is not None:
            prog_cols.append(BarColumn())
            prog_cols.append(MofNCompleteColumn())
        prog_cols.append(_RowSpeedColumn())
        if total_hint is not None:
            prog_cols.append(TimeRemainingColumn())
        prog_cols.append(TimeElapsedColumn())

        use_internal_ui = show_progress and on_rows is None
        progress_ctx = (
            Progress(*prog_cols, console=display.console)
            if use_internal_ui
            else nullcontext()
        )
        with progress_ctx as progress:
            task = (
                progress.add_task(f"→ {desc}", total=total_hint)
                if progress is not None
                else None
            )

            with ProcessPoolExecutor(max_workers=workers) as executor:
                max_inflight = workers * 2
                batches = _read_raw_batches(fh, batch_size)
                futures: deque[Future] = deque()

                for batch in itertools.islice(batches, max_inflight):
                    futures.append(executor.submit(parse, batch))

                while futures:
                    parsed_rows = futures.popleft().result()

                    next_batch = next(batches, None)
                    if next_batch is not None:
                        futures.append(executor.submit(parse, next_batch))

                    if writer is None:
                        schema = static_schema or _infer_schema(col_names, parsed_rows)
                        writer = pq.ParquetWriter(
                            str(parquet_path),
                            schema,
                            compression="zstd",
                            write_statistics=True,
                            use_dictionary=True,
                        )

                    _write_batch(writer, schema, parsed_rows)
                    total_rows += len(parsed_rows)
                    if progress is not None:
                        progress.update(task, advance=len(parsed_rows))
                    if on_rows is not None:
                        on_rows(len(parsed_rows))

        if writer is None:
            # Zero data rows — still emit an empty Parquet so callers can
            # stat() the path and downstream DuckDB composition can read it.
            schema = static_schema or pa.schema(
                [pa.field(n, pa.string()) for n in col_names]
            )
            writer = pq.ParquetWriter(
                str(parquet_path),
                schema,
                compression="zstd",
                write_statistics=True,
                use_dictionary=True,
            )
        writer.close()

    return total_rows


# ---------------------------------------------------------------------------
# ExportPipeline
# ---------------------------------------------------------------------------


class ExportProgress:
    """Persistent two-bar progress UI for the export pipeline.

    Lives for the duration of ``ExportPipeline.run()`` and exposes
    callback-style methods that the pipeline calls as it streams TSV from
    QLever and converts it to Parquet. The two bars track different units
    (bytes vs rows) so they live in separate ``Progress`` instances
    grouped under a single Rich ``Live``.

    When ``enabled=False`` (verbose mode, dashboard mode), all methods
    are no-ops and the original chatter prints take over.
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        total_exports: int = 0,
        console=None,
    ) -> None:
        self._enabled = enabled
        self._console = console or display.console
        self._total_exports = total_exports
        self._completed = 0
        self._tsv_progress: Progress | None = None
        self._cvt_progress: Progress | None = None
        self._live = None
        self._tsv_task = None
        self._cvt_task = None

        if not enabled:
            return

        from rich.console import Group
        from rich.live import Live
        from rich.table import Column

        # Every column is pinned to a fixed width so nothing shifts when
        # values grow (37.2 MB → 1.2 GB, 100k rows → 1M rows, etc.). Long
        # export names ellipsise inside the description column.
        def col(width: int, justify: str = "left") -> Column:
            return Column(width=width, no_wrap=True,
                          overflow="ellipsis", justify=justify)

        # Per-task counter ("3/159") goes in its own column so it doesn't
        # eat into the description width and stays aligned.
        count_fmt = "[dim]{task.fields[count]}[/dim]"
        count_width = max(7, 2 * len(str(total_exports)) + 1)

        self._tsv_progress = Progress(
            SpinnerColumn(),
            TextColumn(count_fmt, table_column=col(count_width, "right")),
            TextColumn(
                "[bold blue]TSV    [/bold blue] {task.description}",
                table_column=col(50),
            ),
            BarColumn(bar_width=40),
            DownloadColumn(table_column=col(20, "right")),
            TransferSpeedColumn(table_column=col(24, "right")),
            TimeElapsedColumn(table_column=col(8, "right")),
            TimeRemainingColumn(table_column=col(8, "right")),
            console=self._console,
        )
        self._cvt_progress = Progress(
            SpinnerColumn(),
            TextColumn(count_fmt, table_column=col(count_width, "right")),
            TextColumn(
                "[bold cyan]Parquet[/bold cyan] {task.description}",
                table_column=col(50),
            ),
            BarColumn(bar_width=40),
            MofNCompleteColumn(table_column=col(20, "right")),
            _RowSpeedColumn(table_column=col(24, "right")),
            TimeElapsedColumn(table_column=col(8, "right")),
            TimeRemainingColumn(table_column=col(8, "right")),
            console=self._console,
        )
        self._live = Live(
            Group(self._tsv_progress, self._cvt_progress),
            console=self._console,
            refresh_per_second=8,
            transient=False,
        )

    def __enter__(self) -> "ExportProgress":
        if not self._enabled:
            return self
        self._live.__enter__()
        self._tsv_task = self._tsv_progress.add_task(
            "[dim]idle[/dim]", total=None, start=False, count="",
        )
        self._cvt_task = self._cvt_progress.add_task(
            "[dim]idle[/dim]", total=None, start=False, count="",
        )
        return self

    def __exit__(self, *args) -> None:
        if self._enabled and self._live is not None:
            self._live.__exit__(*args)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _count_text(self) -> str:
        if self._total_exports > 0:
            return f"{self._completed + 1}/{self._total_exports}"
        return ""

    # -- TSV stream lane ----------------------------------------------------

    def begin_stream(self, name: str) -> None:
        if not self._enabled:
            return
        self._tsv_progress.reset(
            self._tsv_task,
            total=None,
            description=name,
            start=True,
            count=self._count_text(),
        )

    def stream_chunk(self, n: int) -> None:
        if not self._enabled:
            return
        self._tsv_progress.update(self._tsv_task, advance=n)

    def end_stream(self) -> None:
        if not self._enabled:
            return
        self._tsv_progress.stop_task(self._tsv_task)
        self._tsv_progress.update(
            self._tsv_task, description="[dim]idle[/dim]", count="",
        )

    # -- Parquet convert lane ----------------------------------------------

    def begin_convert(self, name: str, total_rows: int) -> None:
        if not self._enabled:
            return
        self._cvt_progress.reset(
            self._cvt_task,
            total=total_rows or None,
            description=name,
            start=True,
            count=self._count_text(),
        )

    def convert_rows(self, n: int) -> None:
        if not self._enabled:
            return
        self._cvt_progress.update(self._cvt_task, advance=n)

    def end_convert(self) -> None:
        """Reset the convert lane to idle. Pure visual; does not advance
        the per-export counter — call ``mark_done`` for that."""
        if not self._enabled:
            return
        self._cvt_progress.stop_task(self._cvt_task)
        self._cvt_progress.update(
            self._cvt_task, description="[dim]idle[/dim]", count="",
        )

    # -- Composite lane (reuses convert bar) -------------------------------

    def begin_composite(self, name: str, total_steps: int) -> None:
        """Use the convert lane to track DuckDB compose step progress."""
        if not self._enabled:
            return
        self._cvt_progress.reset(
            self._cvt_task,
            total=total_steps or None,
            description=f"[magenta]compose[/magenta] {name}",
            start=True,
            count=self._count_text(),
        )

    def composite_step(self, step_name: str) -> None:
        if not self._enabled:
            return
        self._cvt_progress.update(self._cvt_task, advance=1)

    def end_composite(self) -> None:
        """Reset the convert lane to idle after a composite finishes."""
        self.end_convert()

    # -- Misc ---------------------------------------------------------------

    def mark_done(self) -> None:
        """Advance the per-export counter shown in bar descriptions."""
        if self._enabled:
            self._completed += 1

    def log(self, message: str) -> None:
        """Print a line above the live bars (e.g. failures, summaries)."""
        self._console.print(message)


@dataclass
class _PendingConversion:
    """A QueryExport whose TSV is on disk and is being converted to Parquet
    in a background thread, while the next export's SPARQL stream runs."""

    name: str
    future: Future
    parquet_path: Path
    tsv_path: Path


class ExportPipeline:
    """Executes a set of exports: SPARQL→Parquet and DuckDB composition.

    QueryExport runs are pipelined: while one export's TSV is streaming
    from QLever, the previous export's TSV→Parquet conversion runs in a
    background thread (one slot, awaited before submitting the next).
    Composites and dependency checks await the pending conversion first
    so all base Parquets are on disk before they are read.
    """

    def __init__(
        self,
        output_dir: Path,
        exports: dict[str, Export],
        qlever_url: str = f"http://localhost:{QLEVER_PORT}",
        timeout: int = QLEVER_QUERY_TIMEOUT,
        skip_existing: bool = False,
        memory_limit: str = "4GB",
        duckdb_threads: int | None = None,
        temp_directory: Path | None = None,
        dashboard: object | None = None,
        *,
        filters: QueryFilters | None = None,
        keep_base: bool = True,
        reuse_tsv: bool = False,
        http_chunk_size: int = 1_048_576,
        http_connect_timeout: int = 30,
        duckdb_sample_size: int = 100_000,
        duckdb_row_group_size: int = 100_000,
        max_retries: int = DEFAULT_EXPORT_MAX_RETRIES,
        retry_delays: tuple[int, ...] = DEFAULT_EXPORT_RETRY_DELAYS,
        verbose: bool = False,
        chunk_size: int | None = None,
    ) -> None:
        self._output_dir = output_dir
        self._exports = exports
        self._qlever_url = qlever_url
        self._timeout = timeout
        self._skip_existing = skip_existing
        self._memory_limit = memory_limit
        self._duckdb_threads = duckdb_threads
        self._temp_directory = temp_directory
        self._dashboard = dashboard
        self._filters = filters
        self._keep_base = keep_base
        self._reuse_tsv = reuse_tsv
        self._http_chunk_size = http_chunk_size
        self._http_connect_timeout = http_connect_timeout
        self._duckdb_sample_size = duckdb_sample_size
        self._duckdb_row_group_size = duckdb_row_group_size
        self._max_retries = max_retries
        self._retry_delays = retry_delays
        # Default UI is the persistent two-bar Live. Verbose mode and
        # dashboard mode (which already owns its own Live) fall back to
        # plain console prints + ephemeral per-call progress widgets.
        self._verbose = verbose or dashboard is not None
        self._chunk_size = chunk_size if chunk_size and chunk_size > 0 else None
        self._ui: ExportProgress | None = None

    def _path_for(self, export: Export) -> Path:
        """Path of the Parquet artifact produced by *export*.

        - Per-property links scans (``QueryExport`` with ``partition_of``
          set) write to a Hive partition:
          ``<output_dir>/<parent>/x_property=<column>/data.parquet``.
        - Logical ``links`` tables are a directory path — returned so
          callers can test existence as "directory with any partition
          files inside".
        - Everything else is a plain single Parquet file.
        """
        if isinstance(export, QueryExport) and export.partition_of is not None:
            return (
                self._output_dir
                / export.partition_of
                / f"x_property={export.partition_column}"
                / "data.parquet"
            )
        if self._is_links_directory(export):
            return self._output_dir / export.name
        return self._output_dir / f"{export.name}.parquet"

    @staticmethod
    def _is_links_directory(export: Export) -> bool:
        """True if *export* is the no-op aggregator for a Hive links table."""
        return (
            isinstance(export, CompositeExport)
            and not export.compose_steps
            and bool(export.depends_on)
        )

    def _artifact_exists(self, export: Export, path: Path) -> bool:
        """Check whether an export's artifact already exists on disk.

        For a links directory the artifact "exists" iff every declared
        partition file is present.
        """
        if self._is_links_directory(export):
            if not path.is_dir():
                return False
            for dep_name in export.depends_on:
                dep = self._exports_full_registry().get(dep_name)
                if dep is None:
                    return False
                if not self._path_for(dep).exists():
                    return False
            return True
        return path.exists()

    def _exports_full_registry(self) -> dict[str, Export]:
        if not hasattr(self, "_full_registry_cache"):
            self._full_registry_cache = ExportRegistry(filters=self._filters).exports
        return self._full_registry_cache

    def run(self) -> ExportResult:
        """Execute all exports in dependency order."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        result = ExportResult()

        dependency_only: set[str] = set()
        all_exports = self._resolve_dependencies(dependency_only)
        order = self._topological_order(all_exports)

        # Build the persistent two-bar UI unless the user asked for verbose
        # output or a parent dashboard already owns the terminal.
        ui = ExportProgress(
            enabled=not self._verbose,
            total_exports=len(order),
            console=display.console,
        )
        self._ui = ui

        # Single-slot background conversion: while iteration N streams its
        # TSV, iteration N-1's TSV→Parquet runs here. Await before anything
        # that needs the previous Parquet on disk (composite, dep check).
        converter = ThreadPoolExecutor(max_workers=1, thread_name_prefix="convert")
        pending: _PendingConversion | None = None
        try:
            with ui:
                for name in order:
                    export = all_exports[name]
                    parquet_path = self._path_for(export)

                    # Anything that reads previously-produced Parquets needs
                    # the background conversion drained first.
                    if pending is not None and not isinstance(export, QueryExport):
                        pending = self._await_pending(pending, result, dependency_only)

                    if self._skip_existing and self._artifact_exists(export, parquet_path):
                        if self._verbose:
                            display.console.print(f"[dim]Skipping {name} (exists)[/dim]")
                        result.succeeded.append(name)
                        if name not in dependency_only:
                            result.parquet_files.append(parquet_path)
                        ui.mark_done()
                        self._advance_dashboard()
                        continue

                    if isinstance(export, CompositeExport):
                        missing = [
                            dep for dep in export.depends_on
                            if dep not in result.succeeded
                            and not self._path_for(all_exports[dep]).exists()
                        ]
                        if missing:
                            msg = f"Missing dependencies: {', '.join(missing)}"
                            logger.error("Composite export %s skipped: %s", name, msg)
                            ui.log(f"  [red]{name}: SKIPPED — {msg}[/red]")
                            result.failed[name] = msg
                            ui.mark_done()
                            self._advance_dashboard()
                            continue

                    if self._verbose:
                        is_composite = isinstance(export, CompositeExport)
                        if is_composite and self._is_links_directory(export):
                            tag = "[cyan]links[/cyan] [dim](partitioned)[/dim]"
                        elif is_composite:
                            tag = "[cyan]compose[/cyan]"
                        else:
                            tag = "[blue]SPARQL[/blue]"
                            if isinstance(export, QueryExport) and export.partition_of:
                                tag += f" [dim](partition of {export.partition_of})[/dim]"
                        display.console.print(f"\n[bold]━━━ {name} ━━━[/bold] {tag}")
                        if isinstance(export, QueryExport) and export.sparql:
                            display.console.print(f"[dim]{export.sparql}[/dim]")
                    if self._dashboard is not None:
                        try:
                            self._dashboard.set_info("export", name)
                        except Exception:
                            pass

                    try:
                        if isinstance(export, CompositeExport):
                            count, pq_mb = self._run_composite(export, parquet_path)
                            result.succeeded.append(name)
                            if name not in dependency_only:
                                result.parquet_files.append(parquet_path)
                            logger.info("Exported %s: %d rows, %.1f MB", name, count, pq_mb)
                            ui.mark_done()
                            self._advance_dashboard()
                        elif isinstance(export, QueryExport):
                            # Foreground: stream this export's TSV from QLever.
                            # Background (in parallel): the previous export's
                            # TSV→Parquet conversion is running in `pending`.
                            tsv_path, rows = self._stream_query_export(export, parquet_path)
                            # Drain previous conversion before kicking off ours
                            # so we never run two ProcessPools at once.
                            if pending is not None:
                                pending = self._await_pending(pending, result, dependency_only)
                            pending = self._submit_conversion(
                                converter, name, parquet_path, tsv_path, rows,
                            )
                        else:
                            raise TypeError(f"Unknown export type: {type(export)}")

                    except Exception as exc:
                        logger.error("Export failed for %s: %s", name, exc)
                        ui.log(f"  [red]{name}: FAILED — {exc}[/red]")
                        result.failed[name] = str(exc)
                        if isinstance(export, QueryExport):
                            tsv_path = parquet_path.with_suffix(".tsv")
                            _cleanup_partial(tsv_path, parquet_path)
                            ui.end_stream()
                        else:
                            _cleanup_partial(parquet_path)
                        ui.mark_done()
                        self._advance_dashboard()

                # Drain the final background conversion before cleanup/Croissant.
                if pending is not None:
                    pending = self._await_pending(pending, result, dependency_only)
        finally:
            converter.shutdown(wait=True)
            self._ui = None

        # Clean up dependency-only base tables (never delete links partitions).
        if not self._keep_base:
            for exp_name, exp in all_exports.items():
                if exp_name not in dependency_only:
                    continue
                if isinstance(exp, QueryExport) and exp.partition_of is not None:
                    continue
                if self._is_links_directory(exp):
                    continue
                path = self._path_for(exp)
                if path.exists() and path.is_file():
                    path.unlink()
                    logger.info("Removed dependency-only base: %s", exp_name)

        # Generate Croissant metadata.
        if result.succeeded:
            try:
                from .croissant import generate_croissant

                display.console.print("\n[bold]━━━ Croissant metadata ━━━[/bold]")
                generate_croissant(self._output_dir)
            except Exception as exc:
                logger.warning("Croissant generation failed: %s", exc)
                display.console.print(f"  [yellow]Croissant skipped: {exc}[/yellow]")

        self._print_summary(result, dependency_only)
        return result

    # -----------------------------------------------------------------

    def _resolve_dependencies(self, dependency_only: set[str]) -> dict[str, Export]:
        """Add missing dependency exports (from the full registry)."""
        all_exports = dict(self._exports)
        needs_deps = any(isinstance(e, CompositeExport) for e in self._exports.values())
        if not needs_deps:
            return all_exports
        full_registry = ExportRegistry(filters=self._filters).exports
        # BFS from user-requested composites.
        frontier = [
            name for name, exp in self._exports.items()
            if isinstance(exp, CompositeExport)
        ]
        visited: set[str] = set()
        while frontier:
            nxt: list[str] = []
            for n in frontier:
                if n in visited:
                    continue
                visited.add(n)
                exp = all_exports.get(n) or full_registry.get(n)
                if exp is None:
                    continue
                for dep in exp.depends_on:
                    if dep not in all_exports and dep in full_registry:
                        all_exports[dep] = full_registry[dep]
                        dependency_only.add(dep)
                    if dep in full_registry:
                        nxt.append(dep)
            frontier = nxt
        return all_exports

    @staticmethod
    def _topological_order(exports: dict[str, Export]) -> list[str]:
        ordered: list[str] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            export = exports.get(name)
            if export:
                for dep in export.depends_on:
                    visit(dep)
            ordered.append(name)

        for name in exports:
            visit(name)
        return ordered

    def _run_composite(self, export: CompositeExport, parquet_path: Path) -> tuple[int, float]:
        # Links directories aggregate per-property scans via dependencies
        # only — no DuckDB composition to run.
        if not export.compose_steps:
            return self._summarize_links_directory(export, parquet_path)

        # merged_items has its own range-chunked path: aggregate once into
        # sorted Parquet intermediates, then assemble chunks with filter
        # pushdown. Single-connection temp-table composition OOMs on the
        # 60 M CHO dataset; the generic chunked path re-scans the 13 GB
        # links_ore_Proxy directory per chunk.
        if self._chunk_size and export.name == "merged_items":
            return self._run_composite_merged_items(export, parquet_path)

        # group_items: generic shared-then-per-chunk path with CREATE OR
        # REPLACE TEMP TABLE; scalar-only final SELECT is cheap.
        if self._chunk_size and chunked_compose_steps_for(export.name) is not None:
            return self._run_composite_chunked(export, parquet_path)

        ui = self._ui
        if self._verbose:
            threads_info = (
                f", {self._duckdb_threads} threads" if self._duckdb_threads else ""
            )
            display.console.print(
                f"  Composing from base tables "
                f"[dim]({self._memory_limit} memory{threads_info})[/dim]"
            )
        duckdb_tmp = self._temp_directory or (self._output_dir / ".duckdb_tmp")
        dir_str = str(self._output_dir)

        con = duckdb.connect()
        con.execute(f"SET memory_limit = '{self._memory_limit}'")
        con.execute("SET preserve_insertion_order = false")
        if self._duckdb_threads is not None:
            con.execute(f"SET threads = {self._duckdb_threads}")
        if duckdb_tmp is not None:
            duckdb_tmp.mkdir(parents=True, exist_ok=True)
            con.execute(f"SET temp_directory = '{duckdb_tmp}'")

        total = len(export.compose_steps)
        if ui is not None and ui.enabled:
            ui.begin_composite(export.name, total)
        try:
            for i, step in enumerate(export.compose_steps, 1):
                step_sql = step.sql.replace("{exports_dir}", dir_str)
                t0 = time.perf_counter()
                if step.is_final:
                    parquet_path.parent.mkdir(parents=True, exist_ok=True)
                    con.execute(f"""
                        COPY ({step_sql})
                        TO '{parquet_path}'
                        (FORMAT PARQUET, COMPRESSION 'zstd', ROW_GROUP_SIZE {self._duckdb_row_group_size})
                    """)
                    elapsed = time.perf_counter() - t0
                    if self._verbose:
                        display.console.print(
                            f"  [dim][{i}/{total}][/dim] {step.name} ({elapsed:.1f}s)"
                        )
                else:
                    con.execute(step_sql)
                    elapsed = time.perf_counter() - t0
                    if self._verbose:
                        step_count: int = con.execute(
                            f"SELECT COUNT(*) FROM {step.name}"
                        ).fetchone()[0]  # type: ignore[index]
                        display.console.print(
                            f"  [dim][{i}/{total}][/dim] {step.name}: "
                            f"{step_count:,} rows ({elapsed:.1f}s)"
                        )
                if ui is not None and ui.enabled:
                    ui.composite_step(step.name)

            count: int = con.execute(
                f"SELECT COUNT(*) FROM '{parquet_path}'"
            ).fetchone()[0]  # type: ignore[index]
        finally:
            con.close()
            if ui is not None and ui.enabled:
                ui.end_composite()

        pq_mb = parquet_path.stat().st_size / 1e6
        if self._verbose:
            display.console.print(f"  Parquet: {count:,} rows · {pq_mb:.1f} MB")
        return count, pq_mb

    def _run_composite_chunked(
        self, export: CompositeExport, parquet_path: Path
    ) -> tuple[int, float]:
        """Chunked composition for chunkable composites (merged_items,
        group_items).

        Runs the shared steps once, then loops over CHO slices of
        ``self._chunk_size`` rows. Each chunk rebuilds every per-chunk
        temp table narrowed to its slice and writes
        ``<name>_chunk_NN.parquet``. After all chunks exist, they are
        unioned into ``<name>.parquet`` and the chunk files removed. A
        chunk whose Parquet already exists is skipped, making
        interrupted runs resumable.
        """
        ui = self._ui
        chunk_size = self._chunk_size
        assert chunk_size is not None and chunk_size > 0

        step_lists = chunked_compose_steps_for(export.name)
        assert step_lists is not None, (
            f"_run_composite_chunked called for {export.name!r} which "
            "does not support chunking"
        )
        shared, per_chunk = step_lists

        duckdb_tmp = self._temp_directory or (self._output_dir / ".duckdb_tmp")
        dir_str = str(self._output_dir)

        if self._verbose:
            threads_info = (
                f", {self._duckdb_threads} threads" if self._duckdb_threads else ""
            )
            display.console.print(
                f"  Chunked composition "
                f"[dim]({self._memory_limit} memory{threads_info}, "
                f"chunk_size={chunk_size:,})[/dim]"
            )

        con = duckdb.connect()
        con.execute(f"SET memory_limit = '{self._memory_limit}'")
        con.execute("SET preserve_insertion_order = false")
        if self._duckdb_threads is not None:
            con.execute(f"SET threads = {self._duckdb_threads}")
        if duckdb_tmp is not None:
            duckdb_tmp.mkdir(parents=True, exist_ok=True)
            con.execute(f"SET temp_directory = '{duckdb_tmp}'")

        total_chos: int = con.execute(
            f"SELECT COUNT(*) FROM read_parquet("
            f"'{dir_str}/values_edm_ProvidedCHO.parquet')"
        ).fetchone()[0]  # type: ignore[index]
        num_chunks = max(1, math.ceil(total_chos / chunk_size))
        pad = max(2, len(str(num_chunks - 1)))

        if self._verbose:
            display.console.print(
                f"  {total_chos:,} CHOs → {num_chunks} chunk(s) of {chunk_size:,}"
            )

        progress_total = len(shared) + num_chunks * len(per_chunk) + 1  # +1 combine
        if ui is not None and ui.enabled:
            ui.begin_composite(export.name, progress_total)

        try:
            # Shared steps: labels + cho_numbered (built once, reused across chunks).
            for i, step in enumerate(shared, 1):
                sql = step.sql.replace("{exports_dir}", dir_str)
                t0 = time.perf_counter()
                con.execute(sql)
                elapsed = time.perf_counter() - t0
                if self._verbose:
                    display.console.print(
                        f"  [dim][shared {i}/{len(shared)}][/dim] "
                        f"{step.name} ({elapsed:.1f}s)"
                    )
                if ui is not None and ui.enabled:
                    ui.composite_step(step.name)

            # Chunk loop.
            chunk_paths: list[Path] = []
            for idx in range(num_chunks):
                nn = str(idx).zfill(pad)
                chunk_path = self._output_dir / f"{export.name}_chunk_{nn}.parquet"
                chunk_paths.append(chunk_path)

                if chunk_path.exists():
                    if self._verbose:
                        display.console.print(
                            f"  [dim][chunk {nn}/{num_chunks-1}][/dim] "
                            f"skip (exists: {chunk_path.name})"
                        )
                    if ui is not None and ui.enabled:
                        for _ in per_chunk:
                            ui.composite_step("chunk-skip")
                    continue

                chunk_start = idx * chunk_size
                chunk_end = chunk_start + chunk_size  # upper bound; WHERE is safe past total
                chunk_t0 = time.perf_counter()

                for j, step in enumerate(per_chunk, 1):
                    sql = (
                        step.sql
                        .replace("{exports_dir}", dir_str)
                        .replace("{chunk_start}", str(chunk_start))
                        .replace("{chunk_end}", str(chunk_end))
                    )
                    t0 = time.perf_counter()
                    if step.is_final:
                        con.execute(f"""
                            COPY ({sql})
                            TO '{chunk_path}'
                            (FORMAT PARQUET, COMPRESSION 'zstd', ROW_GROUP_SIZE {self._duckdb_row_group_size})
                        """)
                    else:
                        con.execute(sql)
                    elapsed = time.perf_counter() - t0
                    if self._verbose:
                        display.console.print(
                            f"  [dim][chunk {nn} {j}/{len(per_chunk)}][/dim] "
                            f"{step.name} ({elapsed:.1f}s)"
                        )
                    if ui is not None and ui.enabled:
                        ui.composite_step(step.name)

                con.execute("CHECKPOINT")
                if self._verbose:
                    total_elapsed = time.perf_counter() - chunk_t0
                    display.console.print(
                        f"  [magenta]chunk {nn} done[/magenta] "
                        f"({total_elapsed:.1f}s)"
                    )

            # Combine: idempotent union into the final Parquet.
            combine_t0 = time.perf_counter()
            glob_pattern = str(self._output_dir / f"{export.name}_chunk_*.parquet")
            parquet_path.parent.mkdir(parents=True, exist_ok=True)
            con.execute(f"""
                COPY (
                    SELECT * FROM read_parquet(
                        '{glob_pattern}', union_by_name=true
                    )
                )
                TO '{parquet_path}'
                (FORMAT PARQUET, COMPRESSION 'zstd', ROW_GROUP_SIZE {self._duckdb_row_group_size})
            """)
            if self._verbose:
                display.console.print(
                    f"  [magenta]combined {num_chunks} chunk(s)[/magenta] "
                    f"({time.perf_counter()-combine_t0:.1f}s)"
                )
            if ui is not None and ui.enabled:
                ui.composite_step("combine")

            count: int = con.execute(
                f"SELECT COUNT(*) FROM '{parquet_path}'"
            ).fetchone()[0]  # type: ignore[index]
        finally:
            con.close()
            if ui is not None and ui.enabled:
                ui.end_composite()

        # Cleanup only if combine succeeded and final file is on disk.
        if parquet_path.exists():
            for p in chunk_paths:
                if p.exists():
                    p.unlink()

        pq_mb = parquet_path.stat().st_size / 1e6
        if self._verbose:
            display.console.print(f"  Parquet: {count:,} rows · {pq_mb:.1f} MB")
        return count, pq_mb

    def _run_composite_merged_items(
        self, export: CompositeExport, parquet_path: Path
    ) -> tuple[int, float]:
        """Range-chunked composition for merged_items.

        Phase A — prepare: run each ``MergedItemsPrepareSpec`` in its own
        fresh DuckDB connection, materialising a sorted-by-``k_iri``
        Parquet to ``{output_dir}/.merged_items_intermediates/``. Memory
        is bounded by a single spec's hash table and is released between
        specs. Resumable: specs whose output already exists are skipped.

        Phase B — chunk assembly: compute lexicographic ``k_iri`` range
        boundaries once, then for each range open a fresh DuckDB
        connection and COPY one chunk of the final assembly SELECT
        (``merged_items_chunk_sql``). The range predicate on
        ``cho.k_iri`` propagates to every sorted intermediate via DuckDB's
        equi-join filter inference, pruning Parquet row groups and
        keeping per-chunk memory small. Resumable: existing chunk
        Parquets are skipped.

        Phase C — combine: union-by-name glob over chunks into the final
        Parquet, delete chunks, delete intermediates unless
        ``--keep-base`` is set.
        """
        ui = self._ui
        chunk_size = self._chunk_size
        assert chunk_size is not None and chunk_size > 0

        intermediates_dir = self._output_dir / ".merged_items_intermediates"
        duckdb_tmp = self._temp_directory or (self._output_dir / ".duckdb_tmp")
        exports_str = str(self._output_dir)
        intermediates_str = str(intermediates_dir)

        intermediates_dir.mkdir(parents=True, exist_ok=True)
        duckdb_tmp.mkdir(parents=True, exist_ok=True)

        def _fresh_con() -> "duckdb.DuckDBPyConnection":
            con = duckdb.connect()
            con.execute(f"SET memory_limit = '{self._memory_limit}'")
            con.execute("SET preserve_insertion_order = false")
            if self._duckdb_threads is not None:
                con.execute(f"SET threads = {self._duckdb_threads}")
            con.execute(f"SET temp_directory = '{duckdb_tmp}'")
            return con

        specs = merged_items_prepare_specs()

        # Count CHOs up front so we know the chunk count for progress.
        con = _fresh_con()
        try:
            total_chos: int = con.execute(
                f"SELECT COUNT(*) FROM read_parquet("
                f"'{exports_str}/values_edm_ProvidedCHO.parquet')"
            ).fetchone()[0]  # type: ignore[index]
        finally:
            con.close()
        num_chunks = max(1, math.ceil(total_chos / chunk_size))
        pad = max(2, len(str(num_chunks - 1)))
        progress_total = len(specs) + num_chunks + 1  # + combine

        if self._verbose:
            threads_info = (
                f", {self._duckdb_threads} threads" if self._duckdb_threads else ""
            )
            display.console.print(
                f"  Range-chunked via intermediates "
                f"[dim]({self._memory_limit} memory{threads_info}, "
                f"chunk_size={chunk_size:,})[/dim]"
            )
            display.console.print(
                f"  {total_chos:,} CHOs → {num_chunks} chunk(s) of {chunk_size:,}"
            )

        if ui is not None and ui.enabled:
            ui.begin_composite(export.name, progress_total)

        chunk_paths: list[Path] = []
        count = 0
        try:
            # ---- Phase A: prepare intermediates ----
            for i, spec in enumerate(specs, 1):
                out_path = intermediates_dir / spec.filename
                if out_path.exists():
                    if self._verbose:
                        display.console.print(
                            f"  [dim][prep {i}/{len(specs)}][/dim] "
                            f"skip {spec.name} (exists)"
                        )
                    if ui is not None and ui.enabled:
                        ui.composite_step(f"prep/{spec.name}")
                    continue

                sql = (spec.sql
                       .replace("{exports_dir}", exports_str)
                       .replace("{intermediates_dir}", intermediates_str))
                t0 = time.perf_counter()
                con = _fresh_con()
                try:
                    con.execute(
                        f"COPY ({sql}) TO '{out_path}' "
                        f"(FORMAT PARQUET, COMPRESSION 'zstd', "
                        f"ROW_GROUP_SIZE {self._duckdb_row_group_size})"
                    )
                finally:
                    con.close()
                elapsed = time.perf_counter() - t0
                if self._verbose:
                    size_mb = out_path.stat().st_size / 1e6
                    display.console.print(
                        f"  [dim][prep {i}/{len(specs)}][/dim] "
                        f"{spec.name} ({elapsed:.1f}s, {size_mb:.1f} MB)"
                    )
                if ui is not None and ui.enabled:
                    ui.composite_step(f"prep/{spec.name}")

            # ---- Compute chunk range boundaries ----
            con = _fresh_con()
            try:
                rows = con.execute(
                    f"""
                    SELECT k_iri FROM (
                      SELECT k_iri, ROW_NUMBER() OVER (ORDER BY k_iri) AS rn
                      FROM read_parquet('{exports_str}/values_edm_ProvidedCHO.parquet')
                    )
                    WHERE (rn - 1) % {chunk_size} = 0
                    ORDER BY rn
                    """
                ).fetchall()
            finally:
                con.close()
            boundaries: list[str] = [row[0] for row in rows]
            assert len(boundaries) == num_chunks, (
                f"Boundary count {len(boundaries)} != expected {num_chunks}"
            )

            # ---- Phase B: per-chunk COPY ----
            chunk_template = merged_items_chunk_sql()
            for idx in range(num_chunks):
                nn = str(idx).zfill(pad)
                chunk_path = self._output_dir / f"{export.name}_chunk_{nn}.parquet"
                chunk_paths.append(chunk_path)

                if chunk_path.exists():
                    if self._verbose:
                        display.console.print(
                            f"  [dim][chunk {nn}/{num_chunks-1}][/dim] "
                            f"skip (exists: {chunk_path.name})"
                        )
                    if ui is not None and ui.enabled:
                        ui.composite_step(f"chunk/{nn}")
                    continue

                lo = boundaries[idx].replace("'", "''")
                predicate = f"cho.k_iri >= '{lo}'"
                if idx + 1 < num_chunks:
                    hi = boundaries[idx + 1].replace("'", "''")
                    predicate += f" AND cho.k_iri < '{hi}'"

                sql = (chunk_template
                       .replace("{exports_dir}", exports_str)
                       .replace("{intermediates_dir}", intermediates_str)
                       .replace("{range_predicate}", predicate))

                t0 = time.perf_counter()
                con = _fresh_con()
                try:
                    con.execute(
                        f"COPY ({sql}) TO '{chunk_path}' "
                        f"(FORMAT PARQUET, COMPRESSION 'zstd', "
                        f"ROW_GROUP_SIZE {self._duckdb_row_group_size})"
                    )
                finally:
                    con.close()
                elapsed = time.perf_counter() - t0
                if self._verbose:
                    size_mb = chunk_path.stat().st_size / 1e6
                    display.console.print(
                        f"  [dim][chunk {nn}/{num_chunks-1}][/dim] "
                        f"{elapsed:.1f}s, {size_mb:.1f} MB"
                    )
                if ui is not None and ui.enabled:
                    ui.composite_step(f"chunk/{nn}")

            # ---- Phase C: combine chunks ----
            glob_pattern = str(self._output_dir / f"{export.name}_chunk_*.parquet")
            parquet_path.parent.mkdir(parents=True, exist_ok=True)
            combine_t0 = time.perf_counter()
            con = _fresh_con()
            try:
                con.execute(
                    f"COPY ("
                    f"  SELECT * FROM read_parquet("
                    f"    '{glob_pattern}', union_by_name=true"
                    f"  )"
                    f") TO '{parquet_path}' "
                    f"(FORMAT PARQUET, COMPRESSION 'zstd', "
                    f"ROW_GROUP_SIZE {self._duckdb_row_group_size})"
                )
                count = con.execute(
                    f"SELECT COUNT(*) FROM '{parquet_path}'"
                ).fetchone()[0]  # type: ignore[index]
            finally:
                con.close()
            if self._verbose:
                display.console.print(
                    f"  [magenta]combined {num_chunks} chunk(s)[/magenta] "
                    f"({time.perf_counter()-combine_t0:.1f}s)"
                )
            if ui is not None and ui.enabled:
                ui.composite_step("combine")
        finally:
            if ui is not None and ui.enabled:
                ui.end_composite()

        # ---- Cleanup ----
        # Intermediates and chunk Parquets are internal scratch for this
        # composition, not user-facing outputs — always remove once the
        # final Parquet is on disk. ``--keep-base`` governs raw
        # values_* / links_* retention, not these.
        if parquet_path.exists():
            for p in chunk_paths:
                if p.exists():
                    p.unlink()
            if intermediates_dir.exists():
                for f in intermediates_dir.iterdir():
                    if f.is_file():
                        f.unlink()
                try:
                    intermediates_dir.rmdir()
                except OSError:
                    pass

        pq_mb = parquet_path.stat().st_size / 1e6
        if self._verbose:
            display.console.print(f"  Parquet: {count:,} rows · {pq_mb:.1f} MB")
        return count, pq_mb

    def _summarize_links_directory(
        self, export: CompositeExport, dir_path: Path
    ) -> tuple[int, float]:
        """Summarize a Hive-partitioned links directory (no composition)."""
        partition_files = sorted(dir_path.glob("x_property=*/data.parquet"))
        if not partition_files:
            if self._verbose:
                display.console.print("  [yellow]No partition files found.[/yellow]")
            else:
                self._log(f"  [yellow]{export.name}: no partition files[/yellow]")
            return 0, 0.0

        total_bytes = sum(f.stat().st_size for f in partition_files)
        pq_mb = total_bytes / 1e6

        try:
            con = duckdb.connect()
            con.execute(f"SET memory_limit = '{self._memory_limit}'")
            count: int = con.execute(
                f"SELECT COUNT(*) FROM read_parquet("
                f"'{dir_path}/**/*.parquet', hive_partitioning=true)"
            ).fetchone()[0]  # type: ignore[index]
            con.close()
        except Exception as exc:
            logger.warning("Row count for %s failed: %s", export.name, exc)
            count = 0

        if self._verbose:
            display.console.print(
                f"  {len(partition_files)} partitions · {count:,} rows · {pq_mb:.1f} MB"
            )
        return count, pq_mb

    def _stream_query_export(
        self, export: QueryExport, parquet_path: Path,
    ) -> tuple[Path, int]:
        """Foreground step: stream SPARQL TSV from QLever to disk."""
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        tsv_path = parquet_path.with_suffix(".tsv")

        ui = self._ui
        if self._reuse_tsv and tsv_path.exists():
            with open(tsv_path, "rb") as f:
                rows = sum(1 for _ in f) - 1
            tsv_mb = tsv_path.stat().st_size / 1e6
            if self._verbose:
                display.console.print(
                    f"  TSV: {rows:,} rows · {tsv_mb:.1f} MB [dim](reused)[/dim]"
                )
        else:
            on_chunk = ui.stream_chunk if (ui is not None and ui.enabled) else None
            if ui is not None and ui.enabled:
                ui.begin_stream(export.name)
            try:
                rows = run_query_to_tsv(
                    export.sparql, tsv_path, self._qlever_url, self._timeout,
                    max_retries=self._max_retries,
                    retry_delays=self._retry_delays,
                    http_chunk_size=self._http_chunk_size,
                    http_connect_timeout=self._http_connect_timeout,
                    on_chunk=on_chunk,
                )
            finally:
                if ui is not None and ui.enabled:
                    ui.end_stream()
            if self._verbose:
                tsv_mb = tsv_path.stat().st_size / 1e6
                display.console.print(f"  TSV: {rows:,} rows · {tsv_mb:.1f} MB")

        return tsv_path, rows

    def _submit_conversion(
        self,
        converter: ThreadPoolExecutor,
        name: str,
        parquet_path: Path,
        tsv_path: Path,
        rows: int,
    ) -> _PendingConversion:
        """Background step: kick off TSV→Parquet conversion."""
        try:
            from .schema_loader import pyarrow_schema
            pq_schema = pyarrow_schema(name)
        except (KeyError, ImportError):
            pq_schema = None

        ui = self._ui
        on_rows = ui.convert_rows if (ui is not None and ui.enabled) else None
        if ui is not None and ui.enabled:
            ui.begin_convert(name, rows)
        if self._verbose:
            display.console.print("  Converting to Parquet [dim](in background)[/dim]…")
        future = converter.submit(
            tsv_to_parquet,
            tsv_path,
            parquet_path,
            row_group_size=self._duckdb_row_group_size,
            total_hint=rows,
            static_schema=pq_schema,
            show_progress=False,
            on_rows=on_rows,
        )
        return _PendingConversion(
            name=name,
            future=future,
            parquet_path=parquet_path,
            tsv_path=tsv_path,
        )

    def _await_pending(
        self,
        pending: _PendingConversion,
        result: ExportResult,
        dependency_only: set[str],
    ) -> None:
        """Block on a background conversion and record its outcome."""
        ui = self._ui
        try:
            count = pending.future.result()
            pq_mb = pending.parquet_path.stat().st_size / 1e6
            if ui is not None:
                ui.end_convert()
            if self._verbose:
                display.console.print(
                    f"  Parquet {pending.name}: "
                    f"{count:,} rows · {pq_mb:.1f} MB"
                )
            result.succeeded.append(pending.name)
            if pending.name not in dependency_only:
                result.parquet_files.append(pending.parquet_path)
            logger.info(
                "Exported %s: %d rows, %.1f MB", pending.name, count, pq_mb,
            )
            if not self._reuse_tsv:
                try:
                    pending.tsv_path.unlink()
                except FileNotFoundError:
                    pass
        except Exception as exc:
            logger.error("Conversion failed for %s: %s", pending.name, exc)
            if ui is not None:
                ui.end_convert()
            self._log(
                f"  [red]✗ {pending.name}: conversion failed: {exc}[/red]"
            )
            result.failed[pending.name] = str(exc)
            _cleanup_partial(pending.tsv_path, pending.parquet_path)
        if ui is not None:
            ui.mark_done()
        self._advance_dashboard()
        return None

    def _log(self, message: str) -> None:
        """Print a message above the persistent UI (or to plain console)."""
        if self._ui is not None:
            self._ui.log(message)
        else:
            display.console.print(message)

    def _advance_dashboard(self) -> None:
        if self._dashboard is not None:
            try:
                self._dashboard.advance()
            except Exception:
                pass

    @staticmethod
    def _print_summary(result: ExportResult, dependency_only: set[str]) -> None:
        user_succeeded = [n for n in result.succeeded if n not in dependency_only]
        user_failed = {n: e for n, e in result.failed.items() if n not in dependency_only}

        if user_failed:
            display.console.print(
                f"\n[yellow bold]{len(user_failed)} export(s) failed:[/yellow bold]"
            )
            for name, err in user_failed.items():
                display.console.print(f"  [red]{name}: {err}[/red]")
        if result.parquet_files:
            display.console.print(
                f"\n[green bold]{len(user_succeeded)} export(s) complete.[/green bold]"
            )
            for p in result.parquet_files:
                if p.is_dir():
                    parts = list(p.glob("**/*.parquet"))
                    size = sum(f.stat().st_size for f in parts)
                    display.console.print(
                        f"  {p.name}/ ({len(parts)} partitions): "
                        f"{size / 1e6:.1f} MB"
                    )
                else:
                    display.console.print(
                        f"  {p.name}: {p.stat().st_size / 1e6:.1f} MB"
                    )
