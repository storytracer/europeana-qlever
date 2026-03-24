"""Export SPARQL results from QLever to TSV and convert to Parquet.

Uses httpx for streaming HTTP (handles multi-GB responses without loading
into memory) and DuckDB for Parquet conversion (fastest path on ARM64,
zero-copy columnar write with zstd compression).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import httpx
from rich.console import Console
from rich.progress import (
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
)

from .constants import QLEVER_PORT

console = Console()


def run_query_to_tsv(
    query: str,
    output_path: Path,
    qlever_url: str = f"http://localhost:{QLEVER_PORT}",
    timeout: int = 3600,
) -> int:
    """Stream a SPARQL query result from QLever directly to a TSV file.

    Returns approximate row count (newline count minus header).
    """
    total_bytes = 0
    newlines = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"→ {output_path.name}", total=None)

        with httpx.stream(
            "POST",
            qlever_url,
            data={"query": query, "action": "tsv_export"},
            timeout=httpx.Timeout(timeout + 120, connect=30),
        ) as response:
            if response.status_code != 200:
                error_body = response.read().decode("utf-8", errors="replace")[:2000]
                console.print(
                    f"[red]QLever export failed ({response.status_code}):[/red]"
                )
                console.print(error_body)
                response.raise_for_status()

            with open(output_path, "wb") as fh:
                for chunk in response.iter_bytes(chunk_size=1_048_576):
                    fh.write(chunk)
                    total_bytes += len(chunk)
                    newlines += chunk.count(b"\n")
                    progress.update(task, completed=total_bytes)

    return max(0, newlines - 1)


def tsv_to_parquet(
    tsv_path: Path,
    parquet_path: Path,
    *,
    sample_size: int = 100_000,
    row_group_size: int = 100_000,
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

    Returns
    -------
    int
        Number of rows written.
    """
    con = duckdb.connect()
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
) -> list[Path]:
    """Run every registered SPARQL export and convert results to Parquet.

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

    Returns
    -------
    list[Path]
        Paths to the generated Parquet files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_files: list[Path] = []

    for name, query in queries.items():
        tsv_path = output_dir / f"{name}.tsv"
        parquet_path = output_dir / f"{name}.parquet"

        if skip_existing and parquet_path.exists():
            console.print(f"[dim]Skipping {name} (parquet exists)[/dim]")
            parquet_files.append(parquet_path)
            continue

        console.print(f"\n[bold]━━━ {name} ━━━[/bold]")

        # 1. Query → TSV
        rows = run_query_to_tsv(query, tsv_path, qlever_url, timeout)
        tsv_mb = tsv_path.stat().st_size / 1e6
        console.print(f"  TSV: {rows:,} rows · {tsv_mb:.1f} MB")

        # 2. TSV → Parquet
        console.print("  Converting to Parquet…")
        count = tsv_to_parquet(tsv_path, parquet_path)
        pq_mb = parquet_path.stat().st_size / 1e6
        console.print(f"  Parquet: {count:,} rows · {pq_mb:.1f} MB")

        tsv_path.unlink()

        parquet_files.append(parquet_path)

    # Summary
    console.print("\n[green bold]All exports complete.[/green bold]")
    for p in parquet_files:
        console.print(f"  {p.name}: {p.stat().st_size / 1e6:.1f} MB")

    return parquet_files