"""Click CLI for the Europeana EDM → QLever → Parquet pipeline.

Install & run::

    cd ~/dev/europeana-qlever
    uv sync
    uv run europeana-qlever --help

Or for a single command::

    uv run europeana-qlever -w ~/europeana merge /data/TTL --workers 12
    uv run europeana-qlever -w ~/europeana export -q core_metadata
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import click

from . import display
from .constants import (
    EDM_PREFIXES,
    EXPORTS_SUBDIR,
    INDEX_SUBDIR,
    MERGED_SUBDIR,
    QLEVER_INDEX_SETTINGS,
    QLEVER_PORT,
    STATE_FILENAME,
)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="europeana-qlever")
@click.option(
    "-w", "--work-dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    envvar="EUROPEANA_QLEVER_WORK_DIR",
    help="Root working directory for all output (ttl-merged/, index/, exports/).",
)
@click.option(
    "--width", type=int, default=None,
    envvar="EUROPEANA_QLEVER_WIDTH",
    help="Fixed console width (e.g. 50 for phone). Default: auto-detect.",
)
@click.pass_context
def cli(ctx: click.Context, work_dir: Path, width: int | None):
    """Europeana EDM → QLever → Parquet pipeline.

    Ingest ~66 M Europeana Turtle records into a QLever SPARQL engine,
    run analytical queries, and export the results as Parquet files.

    All output is written to subdirectories of WORK_DIR: ttl-merged/,
    index/, and exports/.
    """
    from .state import setup_logging

    if width is not None:
        display.set_width(width)

    ctx.ensure_object(dict)
    ctx.obj["work_dir"] = work_dir
    ctx.obj["merged_dir"] = work_dir / MERGED_SUBDIR
    ctx.obj["index_dir"] = work_dir / INDEX_SUBDIR
    ctx.obj["exports_dir"] = work_dir / EXPORTS_SUBDIR

    setup_logging(work_dir)


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

    display.console.print(table)


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("ttl_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--chunk-size", default=5.0, show_default=True,
              help="Target chunk file size in GB.")
@click.option("--workers", default=4, show_default=True,
              help="Parallel extraction threads.")
@click.option("--sample-size", default=50, show_default=True,
              help="ZIPs to sample for prefix discovery.")
@click.pass_context
def merge(
    ctx: click.Context,
    ttl_dir: Path,
    chunk_size: float,
    workers: int,
    sample_size: int,
):
    """Merge all Europeana TTL ZIPs into chunked, QLever-ready TTL files.

    Reads ZIPs from TTL_DIR and writes merged chunks to
    <work-dir>/ttl-merged/. Strips per-record @prefix/@base declarations,
    prepends a unified prefix block, and splits output into ~CHUNK_SIZE GB
    files. Uses WORKERS parallel threads for ZIP extraction.
    """
    from .merge import merge_ttl, scan_prefixes_from_sample
    from .monitor import ResourceMonitor

    merged_dir: Path = ctx.obj["merged_dir"]
    work_dir: Path = ctx.obj["work_dir"]

    prefixes = scan_prefixes_from_sample(ttl_dir, sample_size=sample_size)
    with ResourceMonitor(work_dir, log_file=work_dir / "monitor.log", console=display.console) as monitor:
        result = merge_ttl(
            ttl_dir,
            merged_dir,
            chunk_size_gb=chunk_size,
            workers=workers,
            prefixes=prefixes,
            monitor=monitor,
        )
    if result.failed_zips:
        display.console.print(
            f"\n[yellow]Warning: {len(result.failed_zips)} ZIP(s) failed "
            f"({result.error_rate:.1%} error rate)[/yellow]"
        )


# ---------------------------------------------------------------------------
# write-qleverfile
# ---------------------------------------------------------------------------

@cli.command("write-qleverfile")
@click.option("--qlever-bin", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None, help="Path to qlever-code/build/ with native binaries.")
@click.option("--docker", is_flag=True, default=False,
              help="Use Docker runtime instead of native binaries.")
@click.option("--port", default=QLEVER_PORT, show_default=True)
@click.option("--stxxl-memory", default="8G", show_default=True,
              help="RAM for external sorting during index build.")
@click.option("--query-memory", default="10G", show_default=True,
              help="RAM budget for query execution.")
@click.option("--cache-size", default="5G", show_default=True,
              help="Query result cache size.")
@click.pass_context
def write_qleverfile_cmd(
    ctx: click.Context,
    qlever_bin: Path | None,
    docker: bool,
    port: int,
    stxxl_memory: str,
    query_memory: str,
    cache_size: str,
):
    """Generate a Qleverfile configured for the Europeana EDM dataset.

    Writes to <work-dir>/index/Qleverfile. Defaults to SYSTEM=native (binaries
    on PATH). Use --qlever-bin to specify a custom binary directory, or --docker
    to use Docker instead.
    """
    index_dir: Path = ctx.obj["index_dir"]
    merged_dir: Path = ctx.obj["merged_dir"]

    if not merged_dir.is_dir():
        display.console.print(f"[red]Merged TTL directory not found: {merged_dir}[/red]")
        raise SystemExit(1)

    index_dir.mkdir(parents=True, exist_ok=True)

    settings_json = json.dumps(QLEVER_INDEX_SETTINGS)

    # Build paths for MULTI_INPUT_JSON and INPUT_FILES.
    # INPUT_FILES must be relative to index_dir (qlever uses pathlib.glob).
    merged_rel = os.path.relpath(merged_dir, index_dir)
    cat_cmd = f"cat {merged_dir}/europeana_*.ttl"

    if docker:
        system_block = """\
[runtime]
SYSTEM = docker
IMAGE = adfreiburg/qlever
"""
    elif qlever_bin is not None:
        system_block = f"""\
[runtime]
SYSTEM = native
QLEVER_BIN_DIR = {qlever_bin}
"""
    else:
        system_block = """\
[runtime]
SYSTEM = native
"""

    qleverfile = f"""\
[data]
NAME = europeana
DESCRIPTION = Europeana metadata
# Data already downloaded via rclone and merged by `europeana-qlever merge`

[index]
INPUT_FILES = {merged_rel}/europeana_*.ttl
MULTI_INPUT_JSON = {{"cmd": "{cat_cmd}", "format": "ttl", "parallel": "true"}}

SETTINGS_JSON = {settings_json}

STXXL_MEMORY = {stxxl_memory}

[server]
PORT = {port}
MEMORY_FOR_QUERIES = {query_memory}
CACHE_MAX_SIZE = {cache_size}
CACHE_MAX_SIZE_SINGLE_ENTRY = 3G
TIMEOUT = 600s
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

    display.console.print(f"[green]Qleverfile written to {display.short_path(qleverfile_path)}[/green]")
    display.console.print(f"[green]settings.json written to {display.short_path(settings_path)}[/green]")
    display.console.print(f"\nNext steps:")
    display.console.print(f"  cd {index_dir}")
    display.console.print(f"  qlever index   # build index")
    display.console.print(f"  qlever start   # serve on :{port}")


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------

@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("qlever_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def index(ctx: click.Context, qlever_args: tuple[str, ...]):
    """Build the QLever index (wraps `qlever index`).

    Runs in <work-dir>/index/, which must contain a Qleverfile. Use
    `write-qleverfile` first if you haven't already. Extra options are
    forwarded to `qlever index` (e.g. --overwrite-existing).
    """
    index_dir: Path = ctx.obj["index_dir"]
    qleverfile = index_dir / "Qleverfile"
    if not qleverfile.exists():
        display.console.print(
            f"[red]No Qleverfile found in {index_dir}.[/red]\n"
            "Run `europeana-qlever write-qleverfile` first."
        )
        raise SystemExit(1)

    if not shutil.which("qlever"):
        display.console.print(
            "[red]`qlever` CLI not found.[/red] "
            "Install it with: pip install qlever --break-system-packages"
        )
        raise SystemExit(1)

    log_path = index_dir / "europeana-index.log"
    display.console.print(f"[bold]Building QLever index in {display.short_path(index_dir)}[/bold]")
    display.console.print(f"Logging to {display.short_path(log_path)}")
    display.console.print("[dim]This typically takes 2–5 hours.[/dim]\n")

    with open(log_path, "w") as log_fh:
        proc = subprocess.Popen(
            ["qlever", "index", *qlever_args],
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
        display.console.print("\n[green bold]Index build complete.[/green bold]")
    else:
        display.console.print(f"\n[red]Index build failed (exit {proc.returncode}).[/red]")
        display.console.print(f"See {log_path} for details.")
        raise SystemExit(proc.returncode)


# ---------------------------------------------------------------------------
# start / stop
# ---------------------------------------------------------------------------

@cli.command()
@click.pass_context
def start(ctx: click.Context):
    """Start the QLever SPARQL server (wraps `qlever start`).

    Runs from <work-dir>/index/. If a server is already running on the
    configured port, it is stopped first.
    """
    index_dir: Path = ctx.obj["index_dir"]
    qleverfile = index_dir / "Qleverfile"
    if not qleverfile.exists():
        display.console.print(f"[red]No Qleverfile in {index_dir}.[/red]")
        raise SystemExit(1)

    # Stop any existing server first
    subprocess.run(["qlever", "stop"], cwd=index_dir,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    display.console.print(f"[bold]Starting QLever server from {display.short_path(index_dir)}[/bold]")
    subprocess.run(["qlever", "start"], cwd=index_dir, check=True)
    display.console.print("[green]Server started.[/green]")


@cli.command()
@click.pass_context
def stop(ctx: click.Context):
    """Stop the QLever SPARQL server (wraps `qlever stop`).

    Runs from <work-dir>/index/.
    """
    index_dir: Path = ctx.obj["index_dir"]
    qleverfile = index_dir / "Qleverfile"
    if not qleverfile.exists():
        display.console.print(f"[red]No Qleverfile in {index_dir}.[/red]")
        raise SystemExit(1)

    display.console.print(f"[bold]Stopping QLever server from {display.short_path(index_dir)}[/bold]")
    subprocess.run(["qlever", "stop"], cwd=index_dir, check=True)
    display.console.print("[green]Server stopped.[/green]")


# ---------------------------------------------------------------------------
# list-queries
# ---------------------------------------------------------------------------

@cli.command("list-queries")
@click.pass_context
def list_queries_cmd(ctx: click.Context):
    """List all available named queries grouped by category."""
    from rich.table import Table

    from .query import QueryBuilder

    qb = QueryBuilder()

    for category, queries in [
        ("Base queries", qb.all_base_queries()),
        ("AI dataset queries", qb.all_ai_queries()),
        ("Analytics queries", qb.all_analytics_queries()),
    ]:
        table = Table(title=category)
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        for name in queries:
            table.add_row(name, qb.describe(name))
        display.console.print(table)
        display.console.print()


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("sparql_files", nargs=-1,
                type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--all", "run_all", is_flag=True, default=False,
              help="Run all base queries (backward-compatible).")
@click.option("-q", "--query", "query_names", multiple=True,
              help="Named query from QueryBuilder (repeatable).")
@click.option("--query-set", type=click.Choice(["base", "ai", "analytics", "all"]),
              help="Run a predefined set of queries.")
@click.option("--country", "countries", multiple=True,
              help="Filter by country (repeatable).")
@click.option("--type", "types", multiple=True,
              help="Filter by edm:type (repeatable).")
@click.option("--rights-category", type=click.Choice(["open", "restricted", "permission"]),
              help="Filter by rights category.")
@click.option("--provider", "providers", multiple=True,
              help="Filter by dataProvider (repeatable).")
@click.option("--min-completeness", type=int,
              help="Minimum completeness score (1-10).")
@click.option("--year-from", type=int, help="Minimum edm:year.")
@click.option("--year-to", type=int, help="Maximum edm:year.")
@click.option("--language", "filter_languages", multiple=True,
              help="Additional language(s) for label resolution beyond English "
                   "and the item's own language. Produces extra columns. Repeatable.")
@click.option("--dataset-name", "dataset_names", multiple=True,
              help="Filter by datasetName (repeatable).")
@click.option("--limit", type=int, help="LIMIT clause for all queries.")
@click.option("--qlever-url", default=f"http://localhost:{QLEVER_PORT}",
              show_default=True, help="QLever HTTP endpoint.")
@click.option("--timeout", default=3600, show_default=True,
              help="Per-query timeout in seconds.")
@click.option("--skip-existing", is_flag=True, default=False,
              help="Skip queries whose .parquet already exists.")
@click.pass_context
def export(
    ctx: click.Context,
    sparql_files: tuple[Path, ...],
    run_all: bool,
    query_names: tuple[str, ...],
    query_set: str | None,
    countries: tuple[str, ...],
    types: tuple[str, ...],
    rights_category: str | None,
    providers: tuple[str, ...],
    min_completeness: int | None,
    year_from: int | None,
    year_to: int | None,
    filter_languages: tuple[str, ...],
    dataset_names: tuple[str, ...],
    limit: int | None,
    qlever_url: str,
    timeout: int,
    skip_existing: bool,
):
    """Export SPARQL query results from QLever as Parquet files.

    Use --all for base queries, --query-set for a category, -q for
    specific named queries, or pass .sparql file paths directly.
    Filter options (--country, --type, etc.) apply to named queries.
    """
    from .export import export_all
    from .query import QueryBuilder, QueryFilters

    # Validate mutually-exclusive modes
    modes = sum([
        bool(run_all),
        bool(query_names),
        bool(query_set),
        bool(sparql_files),
    ])
    if modes == 0:
        raise click.UsageError(
            "Provide one of: --all, -q QUERY, --query-set SET, or .sparql files."
        )
    if modes > 1 and not (bool(query_names) and not run_all and not query_set and not sparql_files):
        # Allow multiple -q flags, but not mixing modes
        if not (modes == 1 or (bool(query_names) and modes == 1)):
            raise click.UsageError(
                "Cannot combine --all, -q, --query-set, and .sparql files."
            )

    # Build filters
    filters = QueryFilters(
        countries=list(countries) or None,
        types=list(types) or None,
        rights_category=rights_category,
        providers=list(providers) or None,
        min_completeness=min_completeness,
        year_from=year_from,
        year_to=year_to,
        languages=list(filter_languages) or None,
        dataset_names=list(dataset_names) or None,
        limit=limit,
    )

    qb = QueryBuilder()
    queries: dict[str, str] = {}

    if sparql_files:
        # Legacy mode: read .sparql files directly
        for p in sparql_files:
            stem = p.stem
            name = re.sub(r"^\d+_", "", stem)
            queries[name] = p.read_text()
    elif run_all:
        queries = qb.all_base_queries(filters)
    elif query_set:
        registry = {
            "base": qb.all_base_queries,
            "ai": qb.all_ai_queries,
            "analytics": qb.all_analytics_queries,
            "all": qb.all_queries,
        }
        queries = registry[query_set](filters)
    elif query_names:
        for name in query_names:
            method = getattr(qb, name, None)
            if method is None or name.startswith("_") or name.startswith("all_"):
                raise click.UsageError(
                    f"Unknown query: '{name}'. Use `list-queries` to see available queries."
                )
            if name == "entity_links":
                queries[name] = method(filters=filters)
            else:
                queries[name] = method(filters)

    exports_dir: Path = ctx.obj["exports_dir"]

    result = export_all(
        output_dir=exports_dir,
        queries=queries,
        qlever_url=qlever_url,
        timeout=timeout,
        skip_existing=skip_existing,
        memory_limit="4GB",
        temp_directory=exports_dir / ".duckdb_tmp",
    )
    if result.failed:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# pipeline — full end-to-end
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("ttl_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--qlever-bin", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None, help="Path to qlever-code/build/ with native binaries.")
@click.option("--docker", is_flag=True, default=False,
              help="Use Docker runtime instead of native binaries.")
@click.option("--workers", default=4, show_default=True,
              help="Parallel extraction threads for merge.")
@click.option("--chunk-size", default=5.0, show_default=True,
              help="Target chunk file size in GB.")
@click.option("--port", default=QLEVER_PORT, show_default=True)
@click.option("--stxxl-memory", default="8G", show_default=True,
              help="RAM for external sorting during index build.")
@click.option("--query-memory", default="10G", show_default=True,
              help="RAM budget for query execution.")
@click.option("--cache-size", default="5G", show_default=True,
              help="Query result cache size.")
@click.option("--timeout", default=3600, show_default=True,
              help="Per-query timeout in seconds for export.")
@click.option("--skip-merge", is_flag=True, help="Skip merge if chunks already exist.")
@click.option("--skip-index", is_flag=True, help="Skip indexing if index already exists.")
@click.option("--force", is_flag=True, default=False,
              help="Ignore checkpoint and start fresh.")
@click.pass_context
def pipeline(
    ctx: click.Context,
    ttl_dir: Path,
    qlever_bin: Path | None,
    docker: bool,
    workers: int,
    chunk_size: float,
    port: int,
    stxxl_memory: str,
    query_memory: str,
    cache_size: str,
    timeout: int,
    skip_merge: bool,
    skip_index: bool,
    force: bool,
):
    """Run the full pipeline: merge → write-qleverfile → index → start → export.

    Takes TTL_DIR (directory of .zip files) and runs all stages in sequence.
    Each stage can be skipped if its output already exists (use --skip-merge,
    --skip-index). Progress is checkpointed to pipeline_state.json so that
    a failed run can be resumed by re-running the same command.

    Use --force to ignore the checkpoint and start fresh.
    """
    import logging

    from .export import export_all
    from .merge import merge_ttl, scan_prefixes_from_sample
    from .monitor import ResourceMonitor
    from .query import QueryBuilder
    from .state import PipelineState

    log = logging.getLogger(__name__)

    work_dir: Path = ctx.obj["work_dir"]
    merged_dir: Path = ctx.obj["merged_dir"]
    index_dir: Path = ctx.obj["index_dir"]
    exports_dir: Path = ctx.obj["exports_dir"]

    # -- Checkpoint state --
    state_path = work_dir / STATE_FILENAME
    if force and state_path.exists():
        state_path.unlink()
        display.console.print("[dim]Checkpoint cleared (--force)[/dim]")

    state = PipelineState.load(state_path) if state_path.exists() else PipelineState.fresh()
    log.info("Pipeline started (force=%s)", force)

    display.console.rule("[bold]Europeana → QLever → Parquet Pipeline[/bold]")

    server_started = False
    failures: list[str] = []

    try:
        with ResourceMonitor(work_dir, log_file=work_dir / "monitor.log", console=display.console) as monitor:

            # --- Stage 1: Merge ---
            chunks = sorted(merged_dir.glob("europeana_*.ttl"))
            if state.is_complete("merge"):
                display.console.print("[dim]Merge already complete (from checkpoint)[/dim]\n")
            elif skip_merge and chunks:
                display.console.print(
                    f"[dim]Skipping merge ({len(chunks)} chunks already in "
                    f"{merged_dir})[/dim]\n"
                )
                state.mark_complete("merge")
            else:
                display.console.rule("[bold cyan]Stage 1 · Merge TTL[/bold cyan]")
                prefixes = scan_prefixes_from_sample(ttl_dir)

                # Resume: skip ZIPs already processed in a prior run
                merge_stage = state.get_stage("merge")
                skip_zips = frozenset(merge_stage.processed_zips)

                merge_result = merge_ttl(
                    ttl_dir, merged_dir,
                    chunk_size_gb=chunk_size, workers=workers, prefixes=prefixes,
                    monitor=monitor, skip_zips=skip_zips,
                )
                state.update_merge(merge_result)
                state.save(state_path)

                if merge_result.failed_zips:
                    msg = (
                        f"Merge: {len(merge_result.failed_zips)} ZIP(s) failed "
                        f"({merge_result.error_rate:.1%} error rate)"
                    )
                    display.console.print(f"[yellow]{msg}[/yellow]")
                    log.warning(msg)
                    failures.append(msg)

            # --- Stage 2: Write Qleverfile ---
            if not state.is_complete("write_qleverfile"):
                display.console.rule("[bold cyan]Stage 2 · Write Qleverfile[/bold cyan]")
                ctx.invoke(
                    write_qleverfile_cmd,
                    qlever_bin=qlever_bin,
                    docker=docker,
                    port=port,
                    stxxl_memory=stxxl_memory,
                    query_memory=query_memory,
                    cache_size=cache_size,
                )
                state.mark_complete("write_qleverfile")
                state.save(state_path)
            else:
                display.console.print("[dim]Qleverfile already written (from checkpoint)[/dim]\n")

            # --- Stage 3: Index ---
            index_exists = any(index_dir.glob("europeana.index.*"))
            if state.is_complete("index"):
                display.console.print("[dim]Index already built (from checkpoint)[/dim]\n")
            elif skip_index and index_exists:
                display.console.print(f"[dim]Skipping index (files exist in {index_dir})[/dim]\n")
                state.mark_complete("index")
                state.save(state_path)
            else:
                display.console.rule("[bold cyan]Stage 3 · Build Index[/bold cyan]")
                ctx.invoke(index, qlever_args=())
                state.mark_complete("index")
                state.save(state_path)

            # --- Stage 4: Start server ---
            display.console.rule("[bold cyan]Stage 4 · Start Server[/bold cyan]")
            ctx.invoke(start)
            server_started = True

            # --- Stage 5: Export ---
            display.console.rule("[bold cyan]Stage 5 · Export to Parquet[/bold cyan]")

            qb = QueryBuilder()
            queries = qb.all_base_queries()

            export_result = export_all(
                output_dir=exports_dir,
                queries=queries,
                qlever_url=f"http://localhost:{port}",
                timeout=timeout,
                skip_existing=True,  # enables natural resume
                memory_limit="4GB",
                temp_directory=exports_dir / ".duckdb_tmp",
            )
            state.update_export(export_result)
            state.save(state_path)

            if export_result.failed:
                for name, err in export_result.failed.items():
                    failures.append(f"Export {name}: {err}")

    except Exception as exc:
        log.exception("Pipeline failed")
        state.mark_failed("pipeline", str(exc))
        state.save(state_path)
        raise
    finally:
        # Always stop server if we started it
        if server_started:
            try:
                display.console.rule("[bold cyan]Stage 6 · Stop Server[/bold cyan]")
                ctx.invoke(stop)
            except Exception:
                log.warning("Failed to stop server during cleanup")
                display.console.print("[yellow]Warning: failed to stop server[/yellow]")

    # -- Final report --
    if failures:
        display.console.rule("[bold yellow]Pipeline completed with errors[/bold yellow]")
        for f in failures:
            display.console.print(f"  [red]- {f}[/red]")
        log.warning("Pipeline completed with %d error(s)", len(failures))
        raise SystemExit(1)
    else:
        display.console.rule("[bold green]Pipeline complete[/bold green]")
        display.console.print(f"Parquet files in: {display.short_path(exports_dir)}")
        log.info("Pipeline completed successfully")
