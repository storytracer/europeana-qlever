"""Export SPARQL results from QLever to TSV and convert to Parquet.

Uses httpx for streaming HTTP (handles multi-GB responses without loading
into memory) and DuckDB for Parquet conversion (fastest path on ARM64,
zero-copy columnar write with zstd compression).

The hybrid pipeline supports both simple SPARQL exports (Phase 1) and
composite DuckDB exports (Phase 2) that join multiple Parquet base tables.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import duckdb
import httpx
from rich.progress import (
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
)

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

_TRANSIENT_STATUS_CODES = {429, 502, 503, 504}


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


def _read_tsv_header(tsv_path: Path) -> list[str]:
    """Read the first line of a TSV and return column names."""
    with open(tsv_path, "r", encoding="utf-8") as fh:
        header_line = fh.readline().strip()
    return header_line.split("\t") if header_line else []


def _strip_question_mark_aliases(columns: list[str]) -> str | None:
    """Build a SELECT clause that strips leading ``?`` from column names.

    Returns ``None`` if no columns need renaming (no ``?`` prefixes).

    .. deprecated:: Use :func:`_build_select_clause` instead.
    """
    needs_rename = any(c.startswith("?") for c in columns)
    if not needs_rename:
        return None
    parts = []
    for col in columns:
        clean = col.lstrip("?")
        if clean != col:
            parts.append(f'"{col}" AS "{clean}"')
        else:
            parts.append(f'"{col}"')
    return ", ".join(parts)


def _build_select_clause(
    columns: list[str],
    varchar_columns: set[str] | None = None,
) -> str:
    """Build a SELECT clause that strips ``?`` prefixes and ``<>`` IRI brackets.

    Every column gets ``?``-prefix removal (QLever TSV headers use ``?item``
    etc.).  VARCHAR columns additionally get a ``CASE WHEN … LIKE '<%%>'``
    guard that strips the angle brackets QLever wraps around IRI values in
    TSV export.  Non-VARCHAR columns (e.g. integers) are passed through
    unchanged to preserve DuckDB's type inference.

    Parameters
    ----------
    columns
        Raw TSV header column names (may have ``?`` prefixes).
    varchar_columns
        Set of column names (with original ``?`` prefix) that DuckDB inferred
        as VARCHAR.  When ``None``, all columns are treated as VARCHAR.
    """
    all_varchar = varchar_columns is None
    parts = []
    for col in columns:
        clean = col.lstrip("?")
        if all_varchar or col in varchar_columns:
            parts.append(
                f"CASE WHEN \"{col}\" LIKE '<%%>' "
                f"THEN SUBSTRING(\"{col}\", 2, LENGTH(\"{col}\") - 2) "
                f"ELSE \"{col}\" END AS \"{clean}\""
            )
        elif clean != col:
            parts.append(f'"{col}" AS "{clean}"')
        else:
            parts.append(f'"{col}"')
    return ", ".join(parts)


def tsv_to_parquet(
    tsv_path: Path,
    parquet_path: Path,
    *,
    sample_size: int = 100_000,
    row_group_size: int = 100_000,
    memory_limit: str = "4GB",
    temp_directory: Path | None = None,
) -> int:
    """Convert a TSV file to Parquet using DuckDB.

    Strips leading ``?`` from QLever TSV column headers so that Parquet
    files have clean column names (e.g. ``item`` instead of ``?item``).

    Parameters
    ----------
    tsv_path : Path
        Input TSV (tab-separated, with header).
    parquet_path : Path
        Output Parquet file path.
    sample_size : int
        Rows sampled for type inference.
    row_group_size : int
        Parquet row group size.
    memory_limit : str
        DuckDB memory budget (e.g. ``"4GB"``). When exceeded, DuckDB
        spills intermediate results to *temp_directory* on disk.
    temp_directory : Path or None
        Directory for DuckDB spill files. Created automatically if set.

    Returns
    -------
    int
        Number of rows written.
    """
    con = duckdb.connect()
    con.execute(f"SET memory_limit = '{memory_limit}'")
    if temp_directory is not None:
        temp_directory.mkdir(parents=True, exist_ok=True)
        con.execute(f"SET temp_directory = '{temp_directory}'")

    # Build SELECT that strips ?-prefixes and <> IRI brackets.
    # First detect which columns DuckDB infers as VARCHAR so we only
    # apply string operations to those (preserving integer types etc.).
    columns = _read_tsv_header(tsv_path)
    csv_src = (
        f"read_csv_auto('{tsv_path}', delim='\\t', header=true, "
        f"sample_size={sample_size}, ignore_errors=true)"
    )
    if columns:
        con.execute(f"CREATE TEMP VIEW _raw AS SELECT * FROM {csv_src}")
        type_rows = con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = '_raw'"
        ).fetchall()
        varchar_cols = {name for name, dtype in type_rows if dtype == "VARCHAR"}
        select_clause = _build_select_clause(columns, varchar_cols)
        con.execute("DROP VIEW _raw")
    else:
        select_clause = "*"

    con.execute(f"""
        COPY (
            SELECT {select_clause} FROM {csv_src}
        )
        TO '{parquet_path}'
        (FORMAT PARQUET, COMPRESSION 'zstd', ROW_GROUP_SIZE {row_group_size})
    """)
    count: int = con.execute(
        f"SELECT COUNT(*) FROM '{parquet_path}'"
    ).fetchone()[0]  # type: ignore[index]
    con.close()
    return count


def _compose_to_parquet(
    spec: QuerySpec,
    output_dir: Path,
    *,
    memory_limit: str = "4GB",
    temp_directory: Path | None = None,
    row_group_size: int = 100_000,
) -> int:
    """Run a DuckDB composition SQL and write the result to Parquet.

    The SQL template uses ``{exports_dir}`` as a placeholder that is
    replaced with the actual *output_dir* path.

    Returns the row count of the output Parquet file.
    """
    assert spec.compose_sql is not None
    parquet_path = output_dir / f"{spec.name}.parquet"

    # Replace the exports_dir placeholder in the SQL template
    sql = spec.compose_sql.replace("{exports_dir}", str(output_dir))

    con = duckdb.connect()
    con.execute(f"SET memory_limit = '{memory_limit}'")
    if temp_directory is not None:
        temp_directory.mkdir(parents=True, exist_ok=True)
        con.execute(f"SET temp_directory = '{temp_directory}'")

    con.execute(f"""
        COPY (
            {sql}
        )
        TO '{parquet_path}'
        (FORMAT PARQUET, COMPRESSION 'zstd', ROW_GROUP_SIZE {row_group_size})
    """)
    count: int = con.execute(
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
    temp_directory: Path | None = None,
    dashboard: object | None = None,
    *,
    keep_base: bool = True,
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
                display.console.print("  Composing from base tables…")
                duckdb_tmp = temp_directory or (output_dir / ".duckdb_tmp")
                count = _compose_to_parquet(
                    spec, output_dir,
                    memory_limit=memory_limit,
                    temp_directory=duckdb_tmp,
                    row_group_size=duckdb_row_group_size,
                )
                pq_mb = parquet_path.stat().st_size / 1e6
                display.console.print(f"  Parquet: {count:,} rows · {pq_mb:.1f} MB")
            else:
                # Phase 1: SPARQL → TSV → Parquet
                assert spec.sparql is not None
                tsv_path = output_dir / f"{name}.tsv"

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
                duckdb_tmp = temp_directory or (output_dir / ".duckdb_tmp")
                count = tsv_to_parquet(
                    tsv_path, parquet_path,
                    memory_limit=memory_limit,
                    temp_directory=duckdb_tmp,
                    sample_size=duckdb_sample_size,
                    row_group_size=duckdb_row_group_size,
                )
                pq_mb = parquet_path.stat().st_size / 1e6
                display.console.print(f"  Parquet: {count:,} rows · {pq_mb:.1f} MB")

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
