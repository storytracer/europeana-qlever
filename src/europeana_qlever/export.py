"""Export SPARQL results from QLever to TSV and convert to Parquet.

Uses httpx for streaming HTTP (handles multi-GB responses without loading
into memory) and DuckDB for Parquet conversion (fastest path on ARM64,
zero-copy columnar write with zstd compression).
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
)
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
            data={"query": query, "action": "tsv_export"},
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
    timeout: int = 3600,
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
    con.execute(f"""
        COPY (
            SELECT * FROM read_csv_auto(
                '{tsv_path}',
                delim='\t',
                header=true,
                sample_size={sample_size},
                ignore_errors=true
            )
        )
        TO '{parquet_path}'
        (FORMAT PARQUET, COMPRESSION 'zstd', ROW_GROUP_SIZE {row_group_size})
    """)
    count: int = con.execute(
        f"SELECT COUNT(*) FROM '{parquet_path}'"
    ).fetchone()[0]  # type: ignore[index]
    con.close()
    return count


def export_all(
    output_dir: Path,
    queries: dict[str, str],
    qlever_url: str = f"http://localhost:{QLEVER_PORT}",
    timeout: int = 3600,
    skip_existing: bool = False,
    memory_limit: str = "4GB",
    temp_directory: Path | None = None,
    dashboard: object | None = None,
    *,
    http_chunk_size: int = 1_048_576,
    http_connect_timeout: int = 30,
    duckdb_sample_size: int = 100_000,
    duckdb_row_group_size: int = 100_000,
    max_retries: int = DEFAULT_EXPORT_MAX_RETRIES,
    retry_delays: tuple[int, ...] = DEFAULT_EXPORT_RETRY_DELAYS,
) -> ExportResult:
    """Run every registered SPARQL export and convert results to Parquet.

    Continues past individual query failures and reports all errors at the
    end.  Returns an :class:`ExportResult` with succeeded/failed lists.

    Parameters
    ----------
    output_dir : Path
        Directory for TSV + Parquet outputs.
    queries : dict[str, str]
        Mapping of query name to SPARQL query text.
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

    for name, query in queries.items():
        tsv_path = output_dir / f"{name}.tsv"
        parquet_path = output_dir / f"{name}.parquet"

        if skip_existing and parquet_path.exists():
            display.console.print(f"[dim]Skipping {name} (parquet exists)[/dim]")
            result.succeeded.append(name)
            result.parquet_files.append(parquet_path)
            if dashboard is not None:
                try:
                    dashboard.advance()
                except Exception:
                    pass
            continue

        display.console.print(f"\n[bold]━━━ {name} ━━━[/bold]")
        if dashboard is not None:
            try:
                dashboard.set_info("query", name)
            except Exception:
                pass

        try:
            # 1. Query → TSV
            rows = run_query_to_tsv(
                query, tsv_path, qlever_url, timeout,
                max_retries=max_retries,
                retry_delays=retry_delays,
                http_chunk_size=http_chunk_size,
                http_connect_timeout=http_connect_timeout,
            )
            tsv_mb = tsv_path.stat().st_size / 1e6
            display.console.print(f"  TSV: {rows:,} rows · {tsv_mb:.1f} MB")

            # 2. TSV → Parquet
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
            result.parquet_files.append(parquet_path)
            logger.info("Exported %s: %d rows, %.1f MB", name, count, pq_mb)

        except Exception as exc:
            logger.error("Export failed for %s: %s", name, exc)
            display.console.print(f"  [red]FAILED: {exc}[/red]")
            result.failed[name] = str(exc)
            _cleanup_partial(tsv_path, parquet_path)

        if dashboard is not None:
            try:
                dashboard.advance()
            except Exception:
                pass

    # Summary
    if result.failed:
        display.console.print(
            f"\n[yellow bold]{len(result.failed)} query(ies) failed:[/yellow bold]"
        )
        for name, err in result.failed.items():
            display.console.print(f"  [red]{name}: {err}[/red]")
    if result.parquet_files:
        display.console.print(
            f"\n[green bold]{len(result.succeeded)} export(s) complete.[/green bold]"
        )
        for p in result.parquet_files:
            display.console.print(f"  {p.name}: {p.stat().st_size / 1e6:.1f} MB")

    return result
