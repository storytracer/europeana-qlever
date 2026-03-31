"""Export SPARQL results from QLever to TSV and convert to Parquet.

Phase 1 streams SPARQL TSV results to disk via httpx, then parses RDF
terms with rdflib and writes Parquet with PyArrow.  Phase 2 uses DuckDB
to compose final exports from multiple Parquet base tables.
"""

from __future__ import annotations

import itertools
import logging
import os
import time
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
from .query import QuerySpec
from .state import ExportResult

logger = logging.getLogger(__name__)

# Suppress rdflib.term warnings about technically-invalid IRIs (e.g. spaces
# in URLs) that are common in real-world Europeana provider data.
logging.getLogger("rdflib.term").setLevel(logging.ERROR)

_TRANSIENT_STATUS_CODES = {429, 502, 503, 504}


class _RowSpeedColumn(ProgressColumn):
    """Displays processing speed as rows/s."""

    def render(self, task: Task) -> Text:
        speed = task.speed
        if speed is None:
            return Text("? rows/s", style="progress.data.speed")
        return Text(f"{speed:,.0f} rows/s", style="progress.data.speed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cleanup_partial(*paths: Path) -> None:
    """Remove partially written files, ignoring errors."""
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
    """Stream a single SPARQL query to a TSV file. Returns approx row count."""
    total_bytes = 0
    newlines = 0

    columns = [
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
    """Return True if the exception looks transient and worth retrying."""
    if isinstance(exc, (httpx.TransportError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _TRANSIENT_STATUS_CODES
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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
    """Stream a SPARQL query result from QLever directly to a TSV file.

    Retries up to *max_retries* times on transient errors.
    Returns approximate row count (newline count minus header).
    """
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

    # Unreachable, but keeps type checker happy
    raise last_exc  # type: ignore[misc]


PARQUET_BATCH_SIZE = 100_000
"""Default number of rows per PyArrow write batch."""


def parse_rdf_term(raw: str) -> str:
    """Parse a SPARQL TSV cell from N-Triples syntax to a clean string value.

    Uses :func:`rdflib.util.from_n3` for proper handling of escape
    sequences, language tags, and datatype suffixes.

    - ``<http://…>``               →  ``http://…``
    - ``"text"@en``                →  ``text``
    - ``"text"``                   →  ``text``
    - ``"42"^^<xsd:integer>``      →  ``42``
    - ``"text with \\"q\\""@en``   →  ``text with "q"``
    - ``IMAGE``                    →  ``IMAGE``  (bare value, unchanged)
    - ``""`` (empty)               →  ``""``
    """
    if not raw:
        return ""
    first = raw[0]
    if first == '"' or first == "<" or raw.startswith("_:"):
        # Delegate to rdflib for proper RDF term parsing.
        # Fall back to manual stripping on malformed values (e.g. trailing
        # backslash that breaks rdflib's escape decoder).
        try:
            term = from_n3(raw)
        except Exception:
            return raw.strip('"<>').split('"')[0]
        if term is None:
            return ""
        return str(term)
    # Bare value (plain literal like IMAGE, Portugal, or integer 42)
    return raw


def _parse_batch(raw_lines: list[str], num_cols: int) -> list[list[str]]:
    """Parse a batch of raw TSV lines with rdflib.  Runs in a worker process."""
    rows = []
    for line in raw_lines:
        cells = line.rstrip("\n").split("\t")
        if len(cells) < num_cols:
            cells.extend([""] * (num_cols - len(cells)))
        elif len(cells) > num_cols:
            cells = cells[:num_cols]
        rows.append([parse_rdf_term(c) for c in cells])
    return rows


def _read_raw_batches(
    fh, batch_size: int
) -> list[str]:
    """Yield batches of raw TSV lines from an open file handle."""
    batch: list[str] = []
    for line in fh:
        batch.append(line)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _infer_schema(col_names: list[str], sample_rows: list[list[str]]) -> pa.Schema:
    """Infer a PyArrow schema from parsed sample rows.

    Columns where every non-empty value is integer-like get ``pa.int64()``,
    float-like get ``pa.float64()``, boolean get ``pa.bool_()``.
    Everything else gets ``pa.string()``.
    """
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
    """Return True if *v* looks like a float (has a decimal point)."""
    try:
        float(v)
        return "." in v
    except ValueError:
        return False


def _make_array(values: tuple, field: pa.Field) -> pa.Array:
    """Convert a tuple of string values to a typed PyArrow array."""
    if field.type == pa.int64():
        return pa.array([int(v) if v else None for v in values], type=pa.int64())
    if field.type == pa.float64():
        return pa.array([float(v) if v else None for v in values], type=pa.float64())
    if field.type == pa.bool_():
        return pa.array([v == "true" if v else None for v in values], type=pa.bool_())
    return pa.array(values, type=pa.string())


def _write_batch(
    writer: pq.ParquetWriter,
    schema: pa.Schema,
    rows: list[list[str]],
) -> None:
    """Convert a batch of parsed rows to a RecordBatch and write to Parquet."""
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
) -> int:
    """Parse a SPARQL TSV file with rdflib and write Parquet with PyArrow.

    Reads raw TSV lines into batches, parses each batch in parallel
    using :class:`~concurrent.futures.ProcessPoolExecutor`, and streams
    parsed results directly to Parquet via :class:`pyarrow.parquet.ParquetWriter`.

    The Parquet schema is inferred from the first batch: columns with
    all-integer values become ``int64``, all-float become ``float64``,
    all-boolean become ``bool``, and everything else is ``string``.

    Parameters
    ----------
    tsv_path : Path
        Input TSV with SPARQL N-Triples serialization.
    parquet_path : Path
        Output Parquet file path.
    batch_size : int
        Rows per parse/write batch.
    row_group_size : int
        Parquet row group size.
    workers : int or None
        Number of parallel parse workers.  Defaults to half the CPU count.
    total_hint : int or None
        Approximate row count for progress display (from the TSV streaming
        step).  When ``None`` a spinner is shown instead of a progress bar.

    Returns
    -------
    int
        Number of rows written.
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

        prog_cols = [SpinnerColumn(), TextColumn("[progress.description]{task.description}")]
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
                # Bounded submission: limit in-flight futures to avoid
                # OOM on large files (executor.map eagerly consumes the
                # entire generator, queuing all batches in memory).
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
                        # Infer schema from first batch
                        schema = _infer_schema(col_names, parsed_rows)
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


def _compose_to_parquet(
    spec: QuerySpec,
    output_dir: Path,
    *,
    memory_limit: str = "4GB",
    threads: int | None = None,
    temp_directory: Path | None = None,
    row_group_size: int = 100_000,
) -> int:
    """Run a DuckDB composition and write the result to Parquet.

    Executes each step in *spec.compose_steps* individually with
    per-step progress logging (row count and elapsed time).  SQL
    templates use ``{exports_dir}`` as a placeholder replaced with
    the actual *output_dir* path.

    Returns the row count of the output Parquet file.
    """
    assert spec.compose_steps is not None
    parquet_path = output_dir / f"{spec.name}.parquet"
    dir_str = str(output_dir)

    con = duckdb.connect()
    con.execute(f"SET memory_limit = '{memory_limit}'")
    if threads is not None:
        con.execute(f"SET threads = {threads}")
    if temp_directory is not None:
        temp_directory.mkdir(parents=True, exist_ok=True)
        con.execute(f"SET temp_directory = '{temp_directory}'")

    total = len(spec.compose_steps)
    for i, step in enumerate(spec.compose_steps, 1):
        step_sql = step.sql.replace("{exports_dir}", dir_str)
        t0 = time.perf_counter()
        if step.is_final:
            con.execute(f"""
                COPY ({step_sql})
                TO '{parquet_path}'
                (FORMAT PARQUET, COMPRESSION 'zstd', ROW_GROUP_SIZE {row_group_size})
            """)
            elapsed = time.perf_counter() - t0
            display.console.print(
                f"  [dim][{i}/{total}][/dim] {step.name} ({elapsed:.1f}s)"
            )
        else:
            con.execute(step_sql)
            elapsed = time.perf_counter() - t0
            count: int = con.execute(
                f"SELECT COUNT(*) FROM {step.name}"
            ).fetchone()[0]  # type: ignore[index]
            display.console.print(
                f"  [dim][{i}/{total}][/dim] {step.name}: "
                f"{count:,} rows ({elapsed:.1f}s)"
            )

    count = con.execute(
        f"SELECT COUNT(*) FROM '{parquet_path}'"
    ).fetchone()[0]  # type: ignore[index]
    con.close()
    return count


def _topological_order(specs: dict[str, QuerySpec]) -> list[str]:
    """Sort spec names so that dependencies come before dependents."""
    ordered: list[str] = []
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        spec = specs.get(name)
        if spec:
            for dep in spec.depends_on:
                visit(dep)
        ordered.append(name)

    for name in specs:
        visit(name)
    return ordered


def export_all(
    output_dir: Path,
    queries: dict[str, QuerySpec],
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
) -> ExportResult:
    """Run all registered exports and convert results to Parquet.

    Handles both simple SPARQL exports (Phase 1) and composite DuckDB
    exports (Phase 2). Composite exports automatically trigger their
    dependencies first.

    Continues past individual query failures and reports all errors at the
    end.  Returns an :class:`ExportResult` with succeeded/failed lists.

    Parameters
    ----------
    output_dir : Path
        Directory for TSV + Parquet outputs.
    queries : dict[str, QuerySpec]
        Mapping of query name to :class:`QuerySpec`.
    qlever_url : str
        QLever HTTP endpoint.
    timeout : int
        Per-query timeout in seconds.
    skip_existing : bool
        Skip queries whose .parquet file already exists.
    memory_limit : str
        DuckDB memory budget for Parquet conversion.
    temp_directory : Path or None
        DuckDB spill directory. Defaults to ``output_dir / ".duckdb_tmp"``.
    dashboard : Dashboard or None
        Optional dashboard for live progress updates.
    keep_base : bool
        Keep intermediate base table Parquet files (default True).
        When False, base tables that were only needed as dependencies
        are removed after composition.
    http_chunk_size : int
        HTTP streaming chunk size in bytes.
    http_connect_timeout : int
        HTTP connect timeout in seconds.
    duckdb_sample_size : int
        DuckDB type inference sample size.
    duckdb_row_group_size : int
        Parquet row group size.
    max_retries : int
        Max retry attempts for transient errors.
    retry_delays : tuple[int, ...]
        Seconds between retry attempts.

    Returns
    -------
    ExportResult
        Outcome with succeeded/failed query lists and Parquet file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    result = ExportResult()

    # Track which base tables are only needed as dependencies
    dependency_only: set[str] = set()
    originally_requested = set(queries.keys())

    # Resolve dependencies: add any specs not already in the dict
    # that are required by composite exports
    from .query import QueryBuilder
    qb = QueryBuilder()

    all_specs = dict(queries)
    for spec in list(queries.values()):
        if spec.is_composite:
            for dep_name in spec.depends_on:
                if dep_name not in all_specs:
                    # Get the dependency query from the builder
                    method = getattr(qb, dep_name, None)
                    if method is not None and not dep_name.startswith("_"):
                        dep_sparql = method()
                        all_specs[dep_name] = QuerySpec(
                            name=dep_name,
                            sparql=dep_sparql,
                        )
                        dependency_only.add(dep_name)

    # Process in topological order (dependencies first)
    order = _topological_order(all_specs)

    for name in order:
        spec = all_specs[name]
        parquet_path = output_dir / f"{name}.parquet"

        if skip_existing and parquet_path.exists():
            display.console.print(f"[dim]Skipping {name} (parquet exists)[/dim]")
            result.succeeded.append(name)
            if name not in dependency_only:
                result.parquet_files.append(parquet_path)
            if dashboard is not None:
                try:
                    dashboard.advance()
                except Exception:
                    pass
            continue

        if spec.is_composite:
            # Check that all dependencies succeeded
            missing = [
                dep for dep in spec.depends_on
                if dep not in result.succeeded
                and not (output_dir / f"{dep}.parquet").exists()
            ]
            if missing:
                msg = f"Missing dependencies: {', '.join(missing)}"
                logger.error("Composite export %s skipped: %s", name, msg)
                display.console.print(f"  [red]SKIPPED: {msg}[/red]")
                result.failed[name] = msg
                if dashboard is not None:
                    try:
                        dashboard.advance()
                    except Exception:
                        pass
                continue

        tag = "[cyan]compose[/cyan]" if spec.is_composite else "[blue]SPARQL[/blue]"
        display.console.print(f"\n[bold]━━━ {name} ━━━[/bold] {tag}")
        if dashboard is not None:
            try:
                dashboard.set_info("query", name)
            except Exception:
                pass

        try:
            if spec.is_composite:
                # Phase 2: DuckDB composition
                threads_info = f", {duckdb_threads} threads" if duckdb_threads else ""
                display.console.print(
                    f"  Composing from base tables "
                    f"[dim]({memory_limit} memory{threads_info})[/dim]"
                )
                duckdb_tmp = temp_directory or (output_dir / ".duckdb_tmp")
                count = _compose_to_parquet(
                    spec, output_dir,
                    memory_limit=memory_limit,
                    threads=duckdb_threads,
                    temp_directory=duckdb_tmp,
                    row_group_size=duckdb_row_group_size,
                )
                pq_mb = parquet_path.stat().st_size / 1e6
                display.console.print(f"  Parquet: {count:,} rows · {pq_mb:.1f} MB")
            else:
                # Phase 1: SPARQL → TSV → Parquet
                assert spec.sparql is not None
                tsv_path = output_dir / f"{name}.tsv"

                if reuse_tsv and tsv_path.exists():
                    # Count lines for progress hint (subtract header)
                    with open(tsv_path, "rb") as f:
                        rows = sum(1 for _ in f) - 1
                    tsv_mb = tsv_path.stat().st_size / 1e6
                    display.console.print(
                        f"  TSV: {rows:,} rows · {tsv_mb:.1f} MB [dim](reused)[/dim]"
                    )
                else:
                    rows = run_query_to_tsv(
                        spec.sparql, tsv_path, qlever_url, timeout,
                        max_retries=max_retries,
                        retry_delays=retry_delays,
                        http_chunk_size=http_chunk_size,
                        http_connect_timeout=http_connect_timeout,
                    )
                    tsv_mb = tsv_path.stat().st_size / 1e6
                    display.console.print(f"  TSV: {rows:,} rows · {tsv_mb:.1f} MB")

                display.console.print("  Converting to Parquet…")
                count = tsv_to_parquet(
                    tsv_path, parquet_path,
                    row_group_size=duckdb_row_group_size,
                    total_hint=rows,
                )
                pq_mb = parquet_path.stat().st_size / 1e6
                display.console.print(f"  Parquet: {count:,} rows · {pq_mb:.1f} MB")

                if not reuse_tsv:
                    tsv_path.unlink()

            result.succeeded.append(name)
            if name not in dependency_only:
                result.parquet_files.append(parquet_path)
            logger.info("Exported %s: %d rows, %.1f MB", name, count, pq_mb)

        except Exception as exc:
            logger.error("Export failed for %s: %s", name, exc)
            display.console.print(f"  [red]FAILED: {exc}[/red]")
            result.failed[name] = str(exc)
            if not spec.is_composite:
                tsv_path = output_dir / f"{name}.tsv"
                _cleanup_partial(tsv_path, parquet_path)
            else:
                _cleanup_partial(parquet_path)

        if dashboard is not None:
            try:
                dashboard.advance()
            except Exception:
                pass

    # Clean up dependency-only base tables if requested
    if not keep_base:
        for dep_name in dependency_only:
            dep_path = output_dir / f"{dep_name}.parquet"
            if dep_path.exists():
                dep_path.unlink()
                logger.info("Removed intermediate base table: %s", dep_name)

    # Summary
    # Filter out dependency-only names from the display
    user_succeeded = [n for n in result.succeeded if n not in dependency_only]
    user_failed = {n: e for n, e in result.failed.items() if n not in dependency_only}

    if user_failed:
        display.console.print(
            f"\n[yellow bold]{len(user_failed)} query(ies) failed:[/yellow bold]"
        )
        for name, err in user_failed.items():
            display.console.print(f"  [red]{name}: {err}[/red]")
    if result.parquet_files:
        display.console.print(
            f"\n[green bold]{len(user_succeeded)} export(s) complete.[/green bold]"
        )
        for p in result.parquet_files:
            display.console.print(f"  {p.name}: {p.stat().st_size / 1e6:.1f} MB")

    return result
