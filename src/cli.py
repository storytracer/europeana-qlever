"""Click CLI for the Europeana EDM → QLever → Parquet pipeline.

Install & run::

    cd ~/dev/europeana-qlever
    uv sync
    uv run europeana-qlever --help

Or for a single command::

    uv run europeana-qlever merge /data/TTL /data/TTL-merged --workers 12
    uv run europeana-qlever export /exports queries/core_metadata.sparql
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from .constants import (
    EDM_PREFIXES,
    QLEVER_INDEX_SETTINGS,
    QLEVER_PORT,
)

console = Console()


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="europeana-qlever")
def cli():
    """Europeana EDM → QLever → Parquet pipeline.

    Ingest ~66 M Europeana Turtle records into a QLever SPARQL engine,
    run analytical queries, and export the results as Parquet files.
    """


# ---------------------------------------------------------------------------
# scan-prefixes
# ---------------------------------------------------------------------------

@cli.command("scan-prefixes")
@click.argument("ttl_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--sample-size", default=50, show_default=True,
              help="Number of ZIPs to sample.")
@click.option("--files-per-zip", default=3, show_default=True,
              help="TTL files to parse inside each sampled ZIP.")
def scan_prefixes_cmd(ttl_dir: Path, sample_size: int, files_per_zip: int):
    """Discover all RDF prefixes used across the Europeana TTL dump.

    Parses a sample of ZIPs with rdflib and prints the merged prefix table.
    The canonical EDM set is always included; extra prefixes are highlighted.
    """
    from rich.table import Table

    from .merge import scan_prefixes_from_sample

    prefixes = scan_prefixes_from_sample(
        ttl_dir, sample_size=sample_size, files_per_zip=files_per_zip
    )

    table = Table(title=f"Prefixes ({len(prefixes)} total)")
    table.add_column("Prefix", style="cyan")
    table.add_column("Namespace URI")
    table.add_column("Source", style="dim")

    for p, u in sorted(prefixes.items()):
        source = "EDM canonical" if p in EDM_PREFIXES else "[bold green]discovered[/]"
        table.add_row(p, u, source)

    console.print(table)


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("ttl_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("merged_dir", type=click.Path(file_okay=False, path_type=Path))
@click.option("--chunk-size", default=5.0, show_default=True,
              help="Target chunk file size in GB.")
@click.option("--workers", default=8, show_default=True,
              help="Parallel extraction threads.")
@click.option("--sample-size", default=50, show_default=True,
              help="ZIPs to sample for prefix discovery.")
def merge(
    ttl_dir: Path,
    merged_dir: Path,
    chunk_size: float,
    workers: int,
    sample_size: int,
):
    """Merge all Europeana TTL ZIPs into chunked, QLever-ready TTL files.

    Strips per-record @prefix/@base declarations, prepends a unified prefix
    block, and splits output into ~CHUNK_SIZE GB files. Uses WORKERS parallel
    threads for ZIP extraction.
    """
    from .merge import merge_ttl, scan_prefixes_from_sample

    prefixes = scan_prefixes_from_sample(ttl_dir, sample_size=sample_size)
    merge_ttl(
        ttl_dir,
        merged_dir,
        chunk_size_gb=chunk_size,
        workers=workers,
        prefixes=prefixes,
    )


# ---------------------------------------------------------------------------
# write-qleverfile
# ---------------------------------------------------------------------------

@cli.command("write-qleverfile")
@click.argument("index_dir", type=click.Path(file_okay=False, path_type=Path))
@click.argument("merged_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--qlever-bin", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None, help="Path to qlever-code/build/ with native binaries.")
@click.option("--port", default=QLEVER_PORT, show_default=True)
@click.option("--stxxl-memory", default="15G", show_default=True,
              help="RAM for external sorting during index build.")
@click.option("--query-memory", default="20G", show_default=True,
              help="RAM budget for query execution.")
@click.option("--cache-size", default="10G", show_default=True,
              help="Query result cache size.")
def write_qleverfile_cmd(
    index_dir: Path,
    merged_dir: Path,
    qlever_bin: Path | None,
    port: int,
    stxxl_memory: str,
    query_memory: str,
    cache_size: str,
):
    """Generate a Qleverfile configured for the Europeana EDM dataset.

    Writes the file to INDEX_DIR/Qleverfile. If --qlever-bin is given, the
    Qleverfile uses SYSTEM=native (no Docker). Otherwise it defaults to Docker.
    """
    index_dir.mkdir(parents=True, exist_ok=True)

    settings_json = json.dumps(QLEVER_INDEX_SETTINGS, indent=2)

    # Build the cat command for MULTI_INPUT_JSON
    cat_cmd = f"cat {merged_dir}/europeana_*.ttl"

    system_block = ""
    if qlever_bin is not None:
        system_block = f"""\
[runtime]
SYSTEM = native
QLEVER_BIN_DIR = {qlever_bin}
"""
    else:
        system_block = """\
[runtime]
SYSTEM = docker
IMAGE = adfreiburg/qlever
"""

    qleverfile = f"""\
[general]
NAME = europeana

[data]
# Data already downloaded via rclone and merged by `europeana-qlever merge`

[index]
MULTI_INPUT_JSON = {{"cmd": "{cat_cmd}", "format": "ttl", "parallel": true}}

SETTINGS_JSON = {settings_json}

STXXL_MEMORY = {stxxl_memory}

[server]
PORT = {port}
MEMORY_FOR_QUERIES = {query_memory}
CACHE_MAX_SIZE = {cache_size}
CACHE_MAX_SIZE_SINGLE_ENTRY = 3G
TIMEOUT = 600
ACCESS_TOKEN =

{system_block}
[ui]
UI_CONFIG = default
UI_PORT = 7000
"""

    qleverfile_path = index_dir / "Qleverfile"
    qleverfile_path.write_text(qleverfile)

    # Also write settings.json for manual qlever-index invocations
    settings_path = index_dir / "settings.json"
    settings_path.write_text(json.dumps(QLEVER_INDEX_SETTINGS, indent=2))

    console.print(f"[green]Qleverfile written to {qleverfile_path}[/green]")
    console.print(f"[green]settings.json written to {settings_path}[/green]")
    console.print(f"\nNext steps:")
    console.print(f"  cd {index_dir}")
    console.print(f"  qlever index   # build the index (~2–5 hours)")
    console.print(f"  qlever start   # launch the SPARQL server on :{port}")


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("index_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def index(index_dir: Path):
    """Build the QLever index (wraps `qlever index`).

    Must be run from the directory containing the Qleverfile. Use
    `write-qleverfile` first if you haven't already.
    """
    qleverfile = index_dir / "Qleverfile"
    if not qleverfile.exists():
        console.print(
            f"[red]No Qleverfile found in {index_dir}.[/red]\n"
            "Run `europeana-qlever write-qleverfile` first."
        )
        raise SystemExit(1)

    if not shutil.which("qlever"):
        console.print(
            "[red]`qlever` CLI not found.[/red] "
            "Install it with: pip install qlever --break-system-packages"
        )
        raise SystemExit(1)

    log_path = index_dir / "europeana-index.log"
    console.print(f"[bold]Building QLever index in {index_dir}[/bold]")
    console.print(f"Logging to {log_path}")
    console.print("[dim]This typically takes 2–5 hours on the DGX Spark.[/dim]\n")

    with open(log_path, "w") as log_fh:
        proc = subprocess.Popen(
            ["qlever", "index"],
            cwd=index_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            log_fh.write(line)
        proc.wait()

    if proc.returncode == 0:
        console.print("\n[green bold]Index build complete.[/green bold]")
    else:
        console.print(f"\n[red]Index build failed (exit {proc.returncode}).[/red]")
        console.print(f"See {log_path} for details.")
        raise SystemExit(proc.returncode)


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("index_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def start(index_dir: Path):
    """Start the QLever SPARQL server (wraps `qlever start`)."""
    qleverfile = index_dir / "Qleverfile"
    if not qleverfile.exists():
        console.print(f"[red]No Qleverfile in {index_dir}.[/red]")
        raise SystemExit(1)

    console.print(f"[bold]Starting QLever server from {index_dir}[/bold]")
    subprocess.run(["qlever", "start"], cwd=index_dir, check=True)
    console.print("[green]Server started.[/green]")


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("output_dir", type=click.Path(file_okay=False, path_type=Path))
@click.argument("sparql_files", nargs=-1, required=True,
                type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--qlever-url", default=f"http://localhost:{QLEVER_PORT}",
              show_default=True, help="QLever HTTP endpoint.")
@click.option("--timeout", default=3600, show_default=True,
              help="Per-query timeout in seconds.")
@click.option("--skip-existing", is_flag=True, default=False,
              help="Skip queries whose .parquet already exists.")
def export(
    output_dir: Path,
    sparql_files: tuple[Path, ...],
    qlever_url: str,
    timeout: int,
    skip_existing: bool,
):
    """Export SPARQL query results from QLever as Parquet files.

    Each .sparql file becomes one TSV (streamed from QLever) and one
    Parquet file (converted via DuckDB with zstd compression).

    The output file name is derived from the .sparql file stem
    (e.g., core_metadata.sparql -> core_metadata.parquet).
    """
    from .export import export_all

    queries = {p.stem: p.read_text() for p in sparql_files}

    export_all(
        output_dir=output_dir,
        queries=queries,
        qlever_url=qlever_url,
        timeout=timeout,
        skip_existing=skip_existing,
    )


# ---------------------------------------------------------------------------
# pipeline — full end-to-end
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("ttl_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("merged_dir", type=click.Path(file_okay=False, path_type=Path))
@click.argument("index_dir", type=click.Path(file_okay=False, path_type=Path))
@click.argument("output_dir", type=click.Path(file_okay=False, path_type=Path))
@click.option("--qlever-bin", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None, help="Path to qlever-code/build/.")
@click.option("--workers", default=8, show_default=True)
@click.option("--chunk-size", default=5.0, show_default=True)
@click.option("--port", default=QLEVER_PORT, show_default=True)
@click.option("--skip-merge", is_flag=True, help="Skip merge if chunks exist.")
@click.option("--skip-index", is_flag=True, help="Skip indexing if index exists.")
@click.option("--queries-dir", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None,
              help="Directory of .sparql files for export. "
                   "Defaults to queries/ in the project root.")
def pipeline(
    ttl_dir: Path,
    merged_dir: Path,
    index_dir: Path,
    output_dir: Path,
    qlever_bin: Path | None,
    workers: int,
    chunk_size: float,
    port: int,
    skip_merge: bool,
    skip_index: bool,
    queries_dir: Path | None,
):
    """Run the full pipeline: merge → index → start → export.

    This is the "do everything" command. Each stage can be skipped if its
    output already exists (use --skip-merge, --skip-index).
    """
    from .export import export_all
    from .merge import merge_ttl, scan_prefixes_from_sample

    console.rule("[bold]Europeana → QLever → Parquet Pipeline[/bold]")

    # --- Stage 1: Merge ---
    chunks = sorted(merged_dir.glob("europeana_*.ttl"))
    if skip_merge and chunks:
        console.print(
            f"[dim]Skipping merge ({len(chunks)} chunks already in "
            f"{merged_dir})[/dim]\n"
        )
    else:
        console.rule("[bold cyan]Stage 1 · Merge TTL[/bold cyan]")
        prefixes = scan_prefixes_from_sample(ttl_dir)
        merge_ttl(
            ttl_dir, merged_dir,
            chunk_size_gb=chunk_size, workers=workers, prefixes=prefixes,
        )

    # --- Stage 2: Write Qleverfile ---
    console.rule("[bold cyan]Stage 2 · Write Qleverfile[/bold cyan]")
    ctx = click.Context(write_qleverfile_cmd)
    ctx.invoke(
        write_qleverfile_cmd,
        index_dir=index_dir,
        merged_dir=merged_dir,
        qlever_bin=qlever_bin,
        port=port,
        stxxl_memory="15G",
        query_memory="20G",
        cache_size="10G",
    )

    # --- Stage 3: Index ---
    index_exists = any(index_dir.glob("europeana.index.*"))
    if skip_index and index_exists:
        console.print(f"[dim]Skipping index (files exist in {index_dir})[/dim]\n")
    else:
        console.rule("[bold cyan]Stage 3 · Build Index[/bold cyan]")
        ctx = click.Context(index)
        ctx.invoke(index, index_dir=index_dir)

    # --- Stage 4: Start server ---
    console.rule("[bold cyan]Stage 4 · Start Server[/bold cyan]")
    ctx = click.Context(start)
    ctx.invoke(start, index_dir=index_dir)

    # --- Stage 5: Export ---
    console.rule("[bold cyan]Stage 5 · Export to Parquet[/bold cyan]")

    if queries_dir is None:
        queries_dir = Path(__file__).resolve().parent.parent.parent / "queries"

    sparql_files = sorted(queries_dir.glob("*.sparql"))
    if not sparql_files:
        console.print(f"[red]No .sparql files found in {queries_dir}[/red]")
        raise SystemExit(1)

    queries = {f.stem: f.read_text() for f in sparql_files}

    export_all(
        output_dir=output_dir,
        queries=queries,
        qlever_url=f"http://localhost:{port}",
    )

    console.rule("[bold green]Pipeline complete[/bold green]")
    console.print(f"Parquet files in: {output_dir}")
