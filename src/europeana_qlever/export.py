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
import os
import time
from datetime import datetime
from collections import deque
from concurrent.futures import Future, ProcessPoolExecutor
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
from .compose import ComposeStep, compose_steps_for
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
) -> int:
    total_bytes = 0
    newlines = 0

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

    with Progress(*columns, console=display.console) as progress:
        task = progress.add_task(f"→ {desc}", total=None)

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
                    progress.update(task, completed=total_bytes)

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
) -> int:
    """Stream a SPARQL query result from QLever directly to a TSV file."""
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return _stream_query(
                query, output_path, qlever_url, timeout,
                http_chunk_size=http_chunk_size,
                http_connect_timeout=http_connect_timeout,
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
) -> int:
    """Parse a SPARQL TSV file with rdflib and write Parquet with PyArrow."""
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

        with Progress(*prog_cols, console=display.console) as progress:
            task = progress.add_task(f"→ {desc}", total=total_hint)

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
                    progress.update(task, advance=len(parsed_rows))

        if writer is not None:
            writer.close()

    return total_rows


# ---------------------------------------------------------------------------
# ExportPipeline
# ---------------------------------------------------------------------------


class ExportPipeline:
    """Executes a set of exports: SPARQL→Parquet and DuckDB composition."""

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
        keep_base: bool = True,
        reuse_tsv: bool = False,
        http_chunk_size: int = 1_048_576,
        http_connect_timeout: int = 30,
        duckdb_sample_size: int = 100_000,
        duckdb_row_group_size: int = 100_000,
        max_retries: int = DEFAULT_EXPORT_MAX_RETRIES,
        retry_delays: tuple[int, ...] = DEFAULT_EXPORT_RETRY_DELAYS,
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
        self._keep_base = keep_base
        self._reuse_tsv = reuse_tsv
        self._http_chunk_size = http_chunk_size
        self._http_connect_timeout = http_connect_timeout
        self._duckdb_sample_size = duckdb_sample_size
        self._duckdb_row_group_size = duckdb_row_group_size
        self._max_retries = max_retries
        self._retry_delays = retry_delays

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
            self._full_registry_cache = ExportRegistry().exports
        return self._full_registry_cache

    def run(self) -> ExportResult:
        """Execute all exports in dependency order."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        result = ExportResult()

        dependency_only: set[str] = set()
        all_exports = self._resolve_dependencies(dependency_only)
        order = self._topological_order(all_exports)

        for name in order:
            export = all_exports[name]
            parquet_path = self._path_for(export)

            if self._skip_existing and self._artifact_exists(export, parquet_path):
                display.console.print(f"[dim]Skipping {name} (exists)[/dim]")
                result.succeeded.append(name)
                if name not in dependency_only:
                    result.parquet_files.append(parquet_path)
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
                    display.console.print(f"  [red]SKIPPED: {msg}[/red]")
                    result.failed[name] = msg
                    self._advance_dashboard()
                    continue

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
                elif isinstance(export, QueryExport):
                    count, pq_mb = self._run_query_export(export, parquet_path)
                else:
                    raise TypeError(f"Unknown export type: {type(export)}")

                result.succeeded.append(name)
                if name not in dependency_only:
                    result.parquet_files.append(parquet_path)
                logger.info("Exported %s: %d rows, %.1f MB", name, count, pq_mb)

            except Exception as exc:
                logger.error("Export failed for %s: %s", name, exc)
                display.console.print(f"  [red]FAILED: {exc}[/red]")
                result.failed[name] = str(exc)
                if isinstance(export, QueryExport):
                    tsv_path = parquet_path.with_suffix(".tsv")
                    _cleanup_partial(tsv_path, parquet_path)
                else:
                    _cleanup_partial(parquet_path)

            self._advance_dashboard()

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
        full_registry = ExportRegistry().exports
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

        threads_info = f", {self._duckdb_threads} threads" if self._duckdb_threads else ""
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
                display.console.print(
                    f"  [dim][{i}/{total}][/dim] {step.name} ({elapsed:.1f}s)"
                )
            else:
                con.execute(step_sql)
                elapsed = time.perf_counter() - t0
                step_count: int = con.execute(
                    f"SELECT COUNT(*) FROM {step.name}"
                ).fetchone()[0]  # type: ignore[index]
                display.console.print(
                    f"  [dim][{i}/{total}][/dim] {step.name}: "
                    f"{step_count:,} rows ({elapsed:.1f}s)"
                )

        count: int = con.execute(
            f"SELECT COUNT(*) FROM '{parquet_path}'"
        ).fetchone()[0]  # type: ignore[index]
        con.close()

        pq_mb = parquet_path.stat().st_size / 1e6
        display.console.print(f"  Parquet: {count:,} rows · {pq_mb:.1f} MB")
        return count, pq_mb

    def _summarize_links_directory(
        self, export: CompositeExport, dir_path: Path
    ) -> tuple[int, float]:
        """Summarize a Hive-partitioned links directory (no composition)."""
        partition_files = sorted(dir_path.glob("x_property=*/data.parquet"))
        if not partition_files:
            display.console.print("  [yellow]No partition files found.[/yellow]")
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

        display.console.print(
            f"  {len(partition_files)} partitions · {count:,} rows · {pq_mb:.1f} MB"
        )
        return count, pq_mb

    def _run_query_export(self, export: QueryExport, parquet_path: Path) -> tuple[int, float]:
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        tsv_path = parquet_path.with_suffix(".tsv")

        if self._reuse_tsv and tsv_path.exists():
            with open(tsv_path, "rb") as f:
                rows = sum(1 for _ in f) - 1
            tsv_mb = tsv_path.stat().st_size / 1e6
            display.console.print(
                f"  TSV: {rows:,} rows · {tsv_mb:.1f} MB [dim](reused)[/dim]"
            )
        else:
            rows = run_query_to_tsv(
                export.sparql, tsv_path, self._qlever_url, self._timeout,
                max_retries=self._max_retries,
                retry_delays=self._retry_delays,
                http_chunk_size=self._http_chunk_size,
                http_connect_timeout=self._http_connect_timeout,
            )
            tsv_mb = tsv_path.stat().st_size / 1e6
            display.console.print(f"  TSV: {rows:,} rows · {tsv_mb:.1f} MB")

        display.console.print("  Converting to Parquet…")
        try:
            from .schema_loader import pyarrow_schema
            pq_schema = pyarrow_schema(export.name)
        except (KeyError, ImportError):
            pq_schema = None
        count = tsv_to_parquet(
            tsv_path, parquet_path,
            row_group_size=self._duckdb_row_group_size,
            total_hint=rows,
            static_schema=pq_schema,
        )
        pq_mb = parquet_path.stat().st_size / 1e6
        display.console.print(f"  Parquet: {count:,} rows · {pq_mb:.1f} MB")

        if not self._reuse_tsv:
            tsv_path.unlink()

        return count, pq_mb

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
