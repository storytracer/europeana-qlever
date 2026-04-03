"""Click CLI for the Europeana EDM → QLever → Parquet pipeline.

Install & run::

    cd ~/dev/europeana-qlever
    uv sync
    uv run europeana-qlever --help

Or for a single command::

    uv run europeana-qlever -d ~/europeana merge /data/TTL --workers 12
    uv run europeana-qlever -d ~/europeana export -q web_resources
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import textwrap
from pathlib import Path

import click

from . import display
from .constants import (
    ANALYSIS_SUBDIR,
    EDM_PREFIXES,
    EXPORTS_SUBDIR,
    INDEX_SUBDIR,
    MERGED_SUBDIR,
    QLEVER_INDEX_SETTINGS,
    QLEVER_PORT,
    QLEVER_QUERY_TIMEOUT,
    STATE_FILENAME,
)
from .export import EXPORT_SETS
from .query import QueryFilters


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="europeana-qlever")
@click.option(
    "-d", "--work-dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    envvar="EUROPEANA_QLEVER_WORK_DIR",
    help="Root working directory for all output (ttl-merged/, index/, exports/).",
)
@click.option(
    "-w", "--width", type=int, default=None,
    envvar="EUROPEANA_QLEVER_WIDTH",
    help="Fixed console width (e.g. 50 for phone). Default: auto-detect.",
)
@click.pass_context
def cli(ctx: click.Context, work_dir: Path, width: int | None):
    """Europeana EDM → QLever → Parquet pipeline.

    Ingest ~66 M Europeana Turtle records into a QLever SPARQL engine,
    run analytical queries, and export the results as Parquet files.

    All output is written to subdirectories of WORK_DIR: ttl-merged/,
    index/, exports/, and analysis/.
    """
    from .resources import ResourceBudget
    from .state import setup_logging

    if width is not None:
        display.set_width(width)

    ctx.ensure_object(dict)
    ctx.obj["work_dir"] = work_dir
    ctx.obj["merged_dir"] = work_dir / MERGED_SUBDIR
    ctx.obj["index_dir"] = work_dir / INDEX_SUBDIR
    ctx.obj["exports_dir"] = work_dir / EXPORTS_SUBDIR
    ctx.obj["analysis_dir"] = work_dir / ANALYSIS_SUBDIR

    budget = ResourceBudget.detect(work_dir)
    ctx.obj["budget"] = budget

    setup_logging(
        work_dir,
        max_bytes=budget.log_max_bytes(),
        backup_count=budget.log_backup_count(),
    )


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
# validate
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("ttl_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--workers", default=0, show_default=True,
              help="Parallel workers (0 = auto-detect).")
@click.option("--no-checksums", is_flag=True, default=False,
              help="Skip MD5 checksum verification.")
@click.pass_context
def validate(
    ctx: click.Context,
    ttl_dir: Path,
    workers: int,
    no_checksums: bool,
):
    """Validate Europeana TTL ZIPs (read-only pre-flight check).

    Verifies MD5 checksums (if .md5sum files exist) and parses every TTL
    entry with rdflib to catch syntax errors. Reports results but does not
    write any files. The merge command validates inline during extraction,
    so this command is optional — useful for inspecting data quality before
    committing to a merge.
    """
    from .validate import validate_all

    budget = ctx.obj["budget"]

    if workers == 0:
        workers = budget.merge_workers()
        display.console.print(f"[dim]Auto-detected {workers} workers[/dim]")

    result = validate_all(
        ttl_dir,
        workers=workers,
        verify_checksums_flag=not no_checksums,
    )

    if result.invalid_entries > 0:
        display.console.print(
            f"\n[yellow]{result.invalid_entries:,} invalid entries would be "
            f"skipped during merge[/yellow]"
        )
        ctx.exit(1)


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("ttl_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--chunk-size", default=5.0, show_default=True,
              help="Target chunk file size in GB.")
@click.option("--workers", default=0, show_default=True,
              help="Parallel extraction threads (0 = auto-detect).")
@click.option("--sample-size", default=50, show_default=True,
              help="ZIPs to sample for prefix discovery.")
@click.option(
    "--checksum-policy",
    type=click.Choice(["skip", "warn", "strict"], case_sensitive=False),
    default="skip",
    show_default=True,
    help="MD5 checksum handling. Default 'skip' because Europeana FTP md5sum "
         "files are unreliable (see README). 'warn' logs mismatches but "
         "continues, 'strict' skips mismatched ZIPs.",
)
@click.pass_context
def merge(
    ctx: click.Context,
    ttl_dir: Path,
    chunk_size: float,
    workers: int,
    sample_size: int,
    checksum_policy: str,
):
    """Merge all Europeana TTL ZIPs into chunked, QLever-ready TTL files.

    Reads ZIPs from TTL_DIR and writes merged chunks to
    <work-dir>/ttl-merged/. Strips per-record @prefix/@base declarations,
    prepends a unified prefix block, and splits output into ~CHUNK_SIZE GB
    files. Each TTL entry is validated with rdflib before writing — invalid
    entries are skipped and logged. Uses WORKERS parallel processes
    (0 = auto-detect based on available CPUs and memory).
    """
    from .merge import merge_ttl, scan_prefixes_from_sample
    from .monitor import ResourceMonitor

    merged_dir: Path = ctx.obj["merged_dir"]
    work_dir: Path = ctx.obj["work_dir"]
    budget = ctx.obj["budget"]

    # Auto-detect workers if not specified
    if workers == 0:
        workers = budget.merge_workers()
        display.console.print(f"[dim]Auto-detected {workers} workers[/dim]")

    prefixes = scan_prefixes_from_sample(ttl_dir, sample_size=sample_size)
    try:
        with ResourceMonitor(
            work_dir,
            log_file=work_dir / "monitor.log",
            console=display.console,
            interval=budget.monitor_idle_interval(),
            active_interval=budget.monitor_active_interval(),
            warn_pct=budget.monitor_warn_pct(),
            critical_pct=budget.monitor_critical_pct(),
        ) as monitor:
            result = merge_ttl(
                ttl_dir,
                merged_dir,
                chunk_size_gb=chunk_size,
                workers=workers,
                prefixes=prefixes,
                monitor=monitor,
                copy_buf_size=budget.copy_buf_size(),
                backpressure_thresholds=budget.backpressure_thresholds(),
                backpressure_sleeps=budget.backpressure_sleeps(),
                cpu_target=budget.cpu_target_pct(),
                cpu_low=budget.cpu_low_pct(),
                throttle_consecutive_samples=budget.throttle_consecutive_samples(),
                writer_join_timeout=budget.writer_join_timeout(),
                checksum_policy=checksum_policy,
            )
    except KeyboardInterrupt:
        display.console.print("\n[yellow]Merge interrupted.[/yellow]")
        raise SystemExit(130)
    if result.failed_zips:
        display.console.print(
            f"\n[yellow]Warning: {len(result.failed_zips)} ZIP(s) failed "
            f"({result.error_rate:.1%} error rate)[/yellow]"
        )


# ---------------------------------------------------------------------------
# write-qleverfile
# ---------------------------------------------------------------------------

def _write_qleverfile(
    index_dir: Path,
    merged_dir: Path,
    budget,
    port: int = QLEVER_PORT,
    qlever_bin: Path | None = None,
    docker: bool = False,
    stxxl_memory: str = "auto",
    query_memory: str = "auto",
    cache_size: str = "auto",
) -> Path:
    """Generate and write a Qleverfile. Returns the path to the written file."""
    # Resolve auto values
    if stxxl_memory == "auto":
        stxxl_memory = budget.qlever_stxxl()
    if query_memory == "auto":
        query_memory = budget.qlever_query_memory()
    if cache_size == "auto":
        cache_size = budget.qlever_cache()

    if not merged_dir.is_dir():
        display.console.print(f"[red]Merged TTL directory not found: {merged_dir}[/red]")
        raise SystemExit(1)

    index_dir.mkdir(parents=True, exist_ok=True)

    # Inject dynamic num-triples-per-batch from budget
    settings = dict(QLEVER_INDEX_SETTINGS)
    settings["num-triples-per-batch"] = budget.qlever_triples_per_batch()
    settings_json = json.dumps(settings)

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
CACHE_MAX_SIZE_SINGLE_ENTRY = {budget.qlever_cache_single_entry()}
TIMEOUT = {budget.qlever_timeout()}s
NUM_THREADS = {budget.qlever_threads()}
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
    settings_path.write_text(json.dumps(settings, indent=2))

    # Write UI configuration with example queries
    _write_ui_config(index_dir, port)

    return qleverfile_path


def _write_ui_config(index_dir: Path, port: int) -> Path:
    """Generate a Qleverfile-ui.yml with lightweight analytics example queries."""
    from .export import ExportRegistry, QueryExport

    registry = ExportRegistry()
    summary_exports = registry.for_set("summary")
    examples = sorted(
        [(name, e.sparql) for name, e in summary_exports.items() if isinstance(e, QueryExport)],
        key=lambda e: e[0],
    )

    hostname = socket.gethostname()

    # Build YAML manually to avoid PyYAML dependency
    lines = [
        "config:",
        "  backend:",
        '    slug: "default"',
        '    name: "Europeana"',
        f'    baseUrl: "http://{hostname}:{port}"',
        "    isDefault: true",
        "    sortKey: 1",
        "    maxDefault: 100",
        '    filteredLanguage: "en"',
        "    dynamicSuggestions: 2",
        "  examples:",
    ]

    for i, (name, sparql) in enumerate(examples, 1):
        lines.append(f'    - name: "{name}"')
        lines.append(f"      sort_key: {i}")
        lines.append("      query: |")
        # Normalize indentation: generated SPARQL has PREFIX lines at col 0
        # but body lines indented from the f-string template. Find the indent
        # of the first non-PREFIX, non-empty line (typically SELECT) and strip
        # that amount from all lines.
        raw_lines = sparql.splitlines()
        body_indent = 0
        for rl in raw_lines:
            if rl.strip() and not rl.startswith("PREFIX"):
                body_indent = len(rl) - len(rl.lstrip())
                break
        for sparql_line in raw_lines:
            if body_indent and sparql_line[:body_indent].isspace():
                stripped = sparql_line[body_indent:]
            else:
                stripped = sparql_line
            lines.append(f"        {stripped}" if stripped.strip() else "")

    ui_config_path = index_dir / "Qleverfile-ui.yml"
    ui_config_path.write_text("\n".join(lines) + "\n")
    return ui_config_path


@cli.command("write-qleverfile")
@click.option("--qlever-bin", type=click.Path(exists=True, file_okay=False, path_type=Path),
              default=None, help="Path to qlever-code/build/ with native binaries.")
@click.option("--docker", is_flag=True, default=False,
              help="Use Docker runtime instead of native binaries.")
@click.option("--port", default=QLEVER_PORT, show_default=True)
@click.option("--stxxl-memory", default="auto", show_default=True,
              help="RAM for external sorting during index build (or 'auto').")
@click.option("--query-memory", default="auto", show_default=True,
              help="RAM budget for query execution (or 'auto').")
@click.option("--cache-size", default="auto", show_default=True,
              help="Query result cache size (or 'auto').")
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
    budget = ctx.obj["budget"]

    qleverfile_path = _write_qleverfile(
        index_dir, merged_dir, budget,
        port=port, qlever_bin=qlever_bin, docker=docker,
        stxxl_memory=stxxl_memory, query_memory=query_memory,
        cache_size=cache_size,
    )
    settings_path = index_dir / "settings.json"
    ui_config_path = index_dir / "Qleverfile-ui.yml"

    display.console.print(f"[green]Qleverfile written to {display.short_path(qleverfile_path)}[/green]")
    display.console.print(f"[green]settings.json written to {display.short_path(settings_path)}[/green]")
    display.console.print(f"[green]Qleverfile-ui.yml written to {display.short_path(ui_config_path)}[/green]")
    display.console.print(f"\nNext steps:")
    display.console.print(f"  cd {index_dir}")
    display.console.print(f"  qlever index   # build index")
    display.console.print(f"  qlever start   # serve on :{port}")
    display.console.print(f"  qlever ui      # launch UI with example queries")


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
            display.console.print(line, end="", highlight=False, markup=False)
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

def _parse_qleverfile(path: Path) -> dict[str, dict[str, str]]:
    """Parse a Qleverfile into ``{section: {key: value}}``."""
    sections: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1]
            current = {}
            sections[section_name] = current
        elif "=" in line and current is not None:
            key, _, value = line.partition("=")
            current[key.strip()] = value.strip()
    return sections


@cli.command()
@click.option("--ui", is_flag=True, default=False,
              help="Also start the QLever UI (wraps `qlever ui`).")
@click.pass_context
def start(ctx: click.Context, ui: bool):
    """Start the QLever SPARQL server (wraps `qlever start`).

    Runs from <work-dir>/index/. If a server is already running on the
    configured port, it is stopped first.  Use --ui to also launch the
    QLever web UI.
    """
    index_dir: Path = ctx.obj["index_dir"]
    merged_dir: Path = ctx.obj["merged_dir"]
    budget = ctx.obj["budget"]
    qleverfile_path = index_dir / "Qleverfile"
    if not qleverfile_path.exists():
        display.console.print(f"[red]No Qleverfile in {index_dir}.[/red]")
        raise SystemExit(1)

    # Preserve non-resource settings from existing Qleverfile, then
    # regenerate with current resource budget.
    old = _parse_qleverfile(qleverfile_path)
    old_runtime = old.get("runtime", {})
    old_server = old.get("server", {})
    docker = old_runtime.get("SYSTEM", "native") == "docker"
    qlever_bin_str = old_runtime.get("QLEVER_BIN_DIR")
    qlever_bin = Path(qlever_bin_str) if qlever_bin_str else None
    port = int(old_server.get("PORT", QLEVER_PORT))

    _write_qleverfile(
        index_dir, merged_dir, budget,
        port=port, qlever_bin=qlever_bin, docker=docker,
    )

    # Display resource budget
    display.console.print(budget.summary_table())
    display.console.print()

    # Parse freshly written Qleverfile and display the server command
    sections = _parse_qleverfile(qleverfile_path)
    data = sections.get("data", {})
    server = sections.get("server", {})
    name = data.get("NAME", "europeana")
    port = server.get("PORT", "7001")
    memory = server.get("MEMORY_FOR_QUERIES", "")
    cache = server.get("CACHE_MAX_SIZE", "")
    cache_entry = server.get("CACHE_MAX_SIZE_SINGLE_ENTRY", "")
    timeout = server.get("TIMEOUT", "")
    threads = server.get("NUM_THREADS", "")

    cmd_parts = ["qlever-server", f"-i {name}", f"-p {port}"]
    if threads:
        cmd_parts.append(f"-j {threads}")
    if memory:
        cmd_parts.append(f"-m {memory}")
    if cache:
        cmd_parts.append(f"-c {cache}")
    if cache_entry:
        cmd_parts.append(f"-e {cache_entry}")
    if timeout:
        cmd_parts.append(f"-s {timeout}")
    display.console.print(f"[bold]Server command:[/bold]  {' '.join(cmd_parts)}")
    display.console.print()

    # Stop any existing server first
    subprocess.run(["qlever", "stop"], cwd=index_dir,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    display.console.print(f"[bold]Starting QLever server from {display.short_path(index_dir)}[/bold]")
    proc = subprocess.run(
        ["qlever", "start"], cwd=index_dir,
        capture_output=True, text=True, check=True,
    )
    if proc.stdout:
        for line in proc.stdout.splitlines():
            display.console.print(line, highlight=False, markup=False)
    display.console.print("[green]Server started.[/green]")

    if ui:
        display.console.print("[bold]Starting QLever UI…[/bold]")
        ui_proc = subprocess.run(
            ["qlever", "ui"], cwd=index_dir,
            capture_output=True, text=True,
        )
        if ui_proc.returncode == 0:
            if ui_proc.stdout:
                for line in ui_proc.stdout.splitlines():
                    display.console.print(line, highlight=False, markup=False)
            display.console.print("[green]UI started.[/green]")
        else:
            stderr = ui_proc.stderr.strip() if ui_proc.stderr else "unknown error"
            display.console.print(f"[yellow]UI failed to start: {stderr}[/yellow]")


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

    # Stop the UI if it's running (qlever ui --stop is a no-op if not active)
    ui_proc = subprocess.run(
        ["qlever", "ui", "--stop"], cwd=index_dir,
        capture_output=True, text=True,
    )
    if ui_proc.returncode == 0 and ui_proc.stdout and "stop" in ui_proc.stdout.lower():
        display.console.print("[green]UI stopped.[/green]")

    display.console.print(f"[bold]Stopping QLever server from {display.short_path(index_dir)}[/bold]")
    subprocess.run(["qlever", "stop"], cwd=index_dir, check=True)
    display.console.print("[green]Server stopped.[/green]")


# ---------------------------------------------------------------------------
# list-exports
# ---------------------------------------------------------------------------

@cli.command("list-exports")
@click.option("--export-set", default=None,
              help="Filter to a specific export set.")
@click.pass_context
def list_exports_cmd(ctx: click.Context, export_set: str | None):
    """List all available exports."""
    from rich.table import Table

    from .export import CompositeExport, ExportRegistry

    registry = ExportRegistry()

    if export_set and export_set != "all":
        if export_set not in EXPORT_SETS:
            available = ", ".join(sorted(EXPORT_SETS))
            raise click.UsageError(
                f"Unknown export set: '{export_set}'. Available: {available}, all"
            )
        exports = registry.for_set(export_set)
    else:
        exports = registry.exports

    table = Table(title=f"Exports ({export_set or 'all'})")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="dim")
    table.add_column("Sets", style="green")
    table.add_column("Description")
    for name, export in exports.items():
        etype = "composite" if isinstance(export, CompositeExport) else "SPARQL"
        member_of = [es.name for es in EXPORT_SETS.values() if name in es.members]
        table.add_row(name, etype, ", ".join(member_of) or "—", export.description)
    display.console.print(table)
    display.console.print()

    if not export_set:
        set_names = ", ".join(sorted(EXPORT_SETS))
        display.console.print(f"[dim]Export sets: {set_names}[/dim]")


# ---------------------------------------------------------------------------
# Shared export resolution helper
# ---------------------------------------------------------------------------

def _resolve_exports(
    names: tuple[str, ...],
    run_all: bool,
    export_set: str | None,
    countries: tuple[str, ...],
    types: tuple[str, ...],
    reuse_level: str | None,
    providers: tuple[str, ...],
    min_completeness: int | None,
    year_from: int | None,
    year_to: int | None,
    filter_languages: tuple[str, ...],
    dataset_names: tuple[str, ...],
    limit: int | None = None,
) -> dict[str, "Export"]:
    """Resolve CLI args into a dict of Export objects."""
    from .export import Export, ExportRegistry

    modes = sum([bool(run_all), bool(names), bool(export_set)])
    if modes == 0:
        raise click.UsageError(
            "Provide one of: NAMES, --all, or --set SET."
        )
    if modes > 1:
        raise click.UsageError(
            "Cannot combine NAMES, --all, and --set."
        )

    filters = QueryFilters(
        countries=list(countries) or None,
        types=list(types) or None,
        reuse_level=reuse_level,
        providers=list(providers) or None,
        min_completeness=min_completeness,
        year_from=year_from,
        year_to=year_to,
        languages=list(filter_languages) or None,
        dataset_names=list(dataset_names) or None,
        limit=limit,
    )

    registry = ExportRegistry(filters=filters)

    if run_all:
        return registry.for_set("pipeline")
    if export_set:
        if export_set == "all":
            return registry.exports
        return registry.for_set(export_set)

    # Positional names
    exports: dict[str, Export] = {}
    for name in names:
        try:
            exports[name] = registry.get(name)
        except KeyError:
            raise click.UsageError(
                f"Unknown export: '{name}'. Use `list-exports` to see available exports."
            )
    return exports


def _analysis_output_path(
    analysis_dir: Path,
    suffix: str,
    output_path: Path | None,
    names: tuple[str, ...],
    export_set: str | None,
    run_all: bool,
    sparql_map: dict[str, str],
) -> Path:
    """Derive the output path for an analysis report."""
    if output_path:
        return output_path
    if names and len(names) == 1:
        stem = names[0]
    elif export_set:
        stem = export_set
    elif run_all:
        stem = "pipeline"
    else:
        stem = "_".join(sorted(sparql_map))
    return analysis_dir / f"{stem}.{suffix}.md"


# ---------------------------------------------------------------------------
# analyze (group)
# ---------------------------------------------------------------------------

@cli.group()
@click.pass_context
def analyze(ctx: click.Context):
    """Analyze SPARQL query performance.

    Use 'analyze qlever' to profile queries against a running QLever
    server, or 'analyze static' for offline structural analysis using
    the SPARQL algebra.
    """


# ---------------------------------------------------------------------------
# analyze qlever
# ---------------------------------------------------------------------------

@analyze.command("qlever")
@click.argument("names", nargs=-1)
@click.option("--all", "run_all", is_flag=True, default=False,
              help="Analyze all pipeline exports.")
@click.option("--set", "export_set", type=click.Choice(list(EXPORT_SETS) + ["all"]),
              help="Analyze a predefined export set.")
@click.option("--country", "countries", multiple=True,
              help="Filter by country (repeatable).")
@click.option("--type", "types", multiple=True,
              help="Filter by edm:type (repeatable).")
@click.option("--reuse-level", type=click.Choice(["open", "restricted", "prohibited"]),
              help="Filter by reuse level.")
@click.option("--provider", "providers", multiple=True,
              help="Filter by dataProvider (repeatable).")
@click.option("--min-completeness", type=int,
              help="Minimum completeness score (1-10).")
@click.option("--year-from", type=int, help="Minimum edm:year.")
@click.option("--year-to", type=int, help="Maximum edm:year.")
@click.option("--language", "filter_languages", multiple=True,
              help="Additional language(s) for label resolution. Repeatable.")
@click.option("--dataset-name", "dataset_names", multiple=True,
              help="Filter by datasetName (repeatable).")
@click.option("--limit", type=int, default=1000, show_default=True,
              help="LIMIT to inject into queries for test runs.")
@click.option("--send", type=int, default=0, show_default=True,
              help="Result rows for QLever to return (0 = metadata only).")
@click.option("-o", "--output", "output_path", type=click.Path(path_type=Path),
              default=None, help="Output Markdown file (default: analysis/<name>.qlever.md).")
@click.option("--qlever-url", default=f"http://localhost:{QLEVER_PORT}",
              show_default=True, help="QLever HTTP endpoint.")
@click.option("--timeout", default=QLEVER_QUERY_TIMEOUT, show_default=True,
              help="Per-query timeout in seconds.")
@click.pass_context
def analyze_qlever(
    ctx: click.Context,
    names: tuple[str, ...],
    run_all: bool,
    export_set: str | None,
    countries: tuple[str, ...],
    types: tuple[str, ...],
    reuse_level: str | None,
    providers: tuple[str, ...],
    min_completeness: int | None,
    year_from: int | None,
    year_to: int | None,
    filter_languages: tuple[str, ...],
    dataset_names: tuple[str, ...],
    limit: int,
    send: int,
    output_path: Path | None,
    qlever_url: str,
    timeout: int,
):
    """Profile exports against a running QLever server.

    Only QueryExports (SPARQL-based) can be analyzed — composite exports
    are skipped.  Runs queries with a LIMIT, collects runtime information
    from the QLever execution tree, and writes a Markdown report.
    """
    from .analysis import analyze_all, render_markdown
    from .export import CompositeExport, QueryExport

    all_exports = _resolve_exports(
        names, run_all, export_set,
        countries, types, reuse_level, providers,
        min_completeness, year_from, year_to, filter_languages,
        dataset_names,
    )

    # Extract SPARQL strings, rejecting composite exports
    sparql_map = {n: e.sparql for n, e in all_exports.items() if isinstance(e, QueryExport)}
    skipped = [n for n, e in all_exports.items() if isinstance(e, CompositeExport)]
    if skipped:
        display.console.print(
            f"[dim]Skipping composite exports (no SPARQL): {', '.join(skipped)}[/dim]"
        )

    analysis_dir: Path = ctx.obj["analysis_dir"]
    out = _analysis_output_path(
        analysis_dir, "qlever", output_path,
        names, export_set, run_all, sparql_map,
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    results = analyze_all(
        sparql_map, qlever_url, timeout,
        send=send, limit=limit,
        describe_fn=lambda n: all_exports[n].description if n in all_exports else "",
    )

    md = render_markdown(results, qlever_url, limit)
    out.write_text(md)

    succeeded = sum(1 for r in results if r.error is None)
    failed = sum(1 for r in results if r.error is not None)
    display.console.print(f"[green]Analysis complete:[/green] {succeeded} ok, {failed} failed")
    display.console.print(f"Report: {out}")

    if failed:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# analyze static
# ---------------------------------------------------------------------------

@analyze.command("static")
@click.argument("names", nargs=-1)
@click.option("--all", "run_all", is_flag=True, default=False,
              help="Analyze all pipeline exports.")
@click.option("--set", "export_set", type=click.Choice(list(EXPORT_SETS) + ["all"]),
              help="Analyze a predefined export set.")
@click.option("--country", "countries", multiple=True,
              help="Filter by country (repeatable).")
@click.option("--type", "types", multiple=True,
              help="Filter by edm:type (repeatable).")
@click.option("--reuse-level", type=click.Choice(["open", "restricted", "prohibited"]),
              help="Filter by reuse level.")
@click.option("--provider", "providers", multiple=True,
              help="Filter by dataProvider (repeatable).")
@click.option("--min-completeness", type=int,
              help="Minimum completeness score (1-10).")
@click.option("--year-from", type=int, help="Minimum edm:year.")
@click.option("--year-to", type=int, help="Maximum edm:year.")
@click.option("--language", "filter_languages", multiple=True,
              help="Additional language(s) for label resolution. Repeatable.")
@click.option("--dataset-name", "dataset_names", multiple=True,
              help="Filter by datasetName (repeatable).")
@click.option("-o", "--output", "output_path", type=click.Path(path_type=Path),
              default=None, help="Output Markdown file (default: analysis/<name>.static.md).")
@click.pass_context
def analyze_static(
    ctx: click.Context,
    names: tuple[str, ...],
    run_all: bool,
    export_set: str | None,
    countries: tuple[str, ...],
    types: tuple[str, ...],
    reuse_level: str | None,
    providers: tuple[str, ...],
    min_completeness: int | None,
    year_from: int | None,
    year_to: int | None,
    filter_languages: tuple[str, ...],
    dataset_names: tuple[str, ...],
    output_path: Path | None,
):
    """Offline structural analysis of SPARQL query complexity.

    Only QueryExports (SPARQL-based) can be analyzed — composite exports
    are skipped.  Parses queries into SPARQL algebra and identifies
    structural bottlenecks without requiring a running QLever server.
    """
    from .analysis import render_static_markdown, static_analyze_all
    from .export import CompositeExport, QueryExport

    all_exports = _resolve_exports(
        names, run_all, export_set,
        countries, types, reuse_level, providers,
        min_completeness, year_from, year_to, filter_languages,
        dataset_names,
    )

    sparql_map = {n: e.sparql for n, e in all_exports.items() if isinstance(e, QueryExport)}
    skipped = [n for n, e in all_exports.items() if isinstance(e, CompositeExport)]
    if skipped:
        display.console.print(
            f"[dim]Skipping composite exports (no SPARQL): {', '.join(skipped)}[/dim]"
        )

    analysis_dir: Path = ctx.obj["analysis_dir"]
    out = _analysis_output_path(
        analysis_dir, "static", output_path,
        names, export_set, run_all, sparql_map,
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    results = static_analyze_all(
        sparql_map, describe_fn=lambda n: all_exports[n].description if n in all_exports else "",
    )

    md = render_static_markdown(results)
    out.write_text(md)

    succeeded = sum(1 for r in results if r.error is None)
    failed = sum(1 for r in results if r.error is not None)
    display.console.print(f"[green]Static analysis complete:[/green] {succeeded} ok, {failed} failed")
    display.console.print(f"Report: {out}")

    if failed:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("names", nargs=-1)
@click.option("--all", "run_all", is_flag=True, default=False,
              help="Run all pipeline exports.")
@click.option("--set", "export_set", type=click.Choice(list(EXPORT_SETS) + ["all"]),
              help="Run a predefined export set.")
@click.option("--country", "countries", multiple=True,
              help="Filter by country (repeatable).")
@click.option("--type", "types", multiple=True,
              help="Filter by edm:type (repeatable).")
@click.option("--reuse-level", type=click.Choice(["open", "restricted", "prohibited"]),
              help="Filter by reuse level.")
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
@click.option("--limit", type=int, help="LIMIT clause for SPARQL exports.")
@click.option("--qlever-url", default=f"http://localhost:{QLEVER_PORT}",
              show_default=True, help="QLever HTTP endpoint.")
@click.option("--timeout", default=QLEVER_QUERY_TIMEOUT, show_default=True,
              help="Per-export timeout in seconds.")
@click.option("--skip-existing", is_flag=True, default=False,
              help="Skip exports whose .parquet already exists.")
@click.option("--duckdb-memory", default="auto", show_default=True,
              help="DuckDB memory budget (e.g. '4GB' or 'auto').")
@click.option("--keep-base/--no-keep-base", default=True, show_default=True,
              help="Keep intermediate base table Parquet files after composition. "
                   "Use --no-keep-base to clean them up.")
@click.option("--reuse-tsv", is_flag=True, default=False,
              help="Skip SPARQL download if the .tsv file already exists. "
                   "Useful for re-testing Parquet conversion without re-downloading.")
@click.pass_context
def export(
    ctx: click.Context,
    names: tuple[str, ...],
    run_all: bool,
    export_set: str | None,
    countries: tuple[str, ...],
    types: tuple[str, ...],
    reuse_level: str | None,
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
    duckdb_memory: str,
    keep_base: bool,
    reuse_tsv: bool,
):
    """Export data from QLever as Parquet files.

    Pass export names as positional arguments, use --all for the full
    pipeline, or --set for a named export set.  Filter options
    (--country, --type, etc.) apply to SPARQL-based exports.

    Composite exports (like items_enriched) automatically export their
    dependencies first, then compose the final Parquet via DuckDB.
    Use --no-keep-base to clean up intermediate base table files.
    """
    from .export import ExportPipeline

    exports = _resolve_exports(
        names, run_all, export_set,
        countries, types, reuse_level, providers,
        min_completeness, year_from, year_to, filter_languages,
        dataset_names, limit=limit,
    )

    exports_dir: Path = ctx.obj["exports_dir"]

    budget = ctx.obj["budget"]

    if duckdb_memory == "auto":
        duckdb_memory = budget.duckdb_memory()

    result = ExportPipeline(
        output_dir=exports_dir,
        exports=exports,
        qlever_url=qlever_url,
        timeout=timeout,
        skip_existing=skip_existing,
        memory_limit=duckdb_memory,
        duckdb_threads=budget.duckdb_threads(),
        temp_directory=exports_dir / ".duckdb_tmp",
        keep_base=keep_base,
        reuse_tsv=reuse_tsv,
        http_chunk_size=budget.http_chunk_size(),
        http_connect_timeout=budget.http_connect_timeout(),
        duckdb_sample_size=budget.duckdb_sample_size(),
        duckdb_row_group_size=budget.duckdb_row_group_size(),
        max_retries=budget.export_max_retries(),
        retry_delays=budget.export_retry_delays(),
    ).run()
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
@click.option("--workers", default=0, show_default=True,
              help="Parallel extraction threads for merge (0 = auto-detect).")
@click.option("--chunk-size", default=5.0, show_default=True,
              help="Target chunk file size in GB.")
@click.option("--port", default=QLEVER_PORT, show_default=True)
@click.option("--stxxl-memory", default="auto", show_default=True,
              help="RAM for external sorting during index build (or 'auto').")
@click.option("--query-memory", default="auto", show_default=True,
              help="RAM budget for query execution (or 'auto').")
@click.option("--cache-size", default="auto", show_default=True,
              help="Query result cache size (or 'auto').")
@click.option("--duckdb-memory", default="auto", show_default=True,
              help="DuckDB memory budget for export (e.g. '4GB' or 'auto').")
@click.option("--timeout", default=QLEVER_QUERY_TIMEOUT, show_default=True,
              help="Per-query timeout in seconds for export.")
@click.option("--skip-merge", is_flag=True, help="Skip merge if chunks already exist.")
@click.option("--skip-index", is_flag=True, help="Skip indexing if index already exists.")
@click.option("--force", is_flag=True, default=False,
              help="Ignore checkpoint and start fresh.")
@click.option(
    "--checksum-policy",
    type=click.Choice(["skip", "warn", "strict"], case_sensitive=False),
    default="skip",
    show_default=True,
    help="MD5 checksum handling for merge stage. Default 'skip' because "
         "Europeana FTP md5sum files are unreliable (see README).",
)
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
    duckdb_memory: str,
    timeout: int,
    skip_merge: bool,
    skip_index: bool,
    force: bool,
    checksum_policy: str,
):
    """Run the full pipeline: merge → write-qleverfile → index → start → export.

    Takes TTL_DIR (directory of .zip files) and runs all stages in sequence.
    Each stage can be skipped if its output already exists (use --skip-merge,
    --skip-index). Progress is checkpointed to pipeline_state.json so that
    a failed run can be resumed by re-running the same command.

    Resource allocation (workers, memory) is auto-detected from your system
    unless overridden with explicit values. Use --force to ignore the
    checkpoint and start fresh.
    """
    import logging

    from .dashboard import Dashboard
    from .export import ExportPipeline, ExportRegistry
    from .merge import merge_ttl, scan_prefixes_from_sample
    from .monitor import ResourceMonitor
    from .state import PipelineState

    log = logging.getLogger(__name__)

    work_dir: Path = ctx.obj["work_dir"]
    merged_dir: Path = ctx.obj["merged_dir"]
    index_dir: Path = ctx.obj["index_dir"]
    exports_dir: Path = ctx.obj["exports_dir"]
    budget = ctx.obj["budget"]

    if workers == 0:
        workers = budget.merge_workers()
    if stxxl_memory == "auto":
        stxxl_memory = budget.qlever_stxxl()
    if query_memory == "auto":
        query_memory = budget.qlever_query_memory()
    if cache_size == "auto":
        cache_size = budget.qlever_cache()
    if duckdb_memory == "auto":
        duckdb_memory = budget.duckdb_memory()

    # -- Checkpoint state --
    state_path = work_dir / STATE_FILENAME
    if force and state_path.exists():
        state_path.unlink()
        display.console.print("[dim]Checkpoint cleared (--force)[/dim]")

    state = PipelineState.load(state_path) if state_path.exists() else PipelineState.fresh()
    log.info("Pipeline started (force=%s)", force)

    display.console.rule("[bold]Europeana → QLever → Parquet Pipeline[/bold]")
    display.console.print(budget.summary_table())

    server_started = False
    failures: list[str] = []

    try:
        with ResourceMonitor(
            work_dir,
            log_file=work_dir / "monitor.log",
            console=display.console,
            interval=budget.monitor_idle_interval(),
            active_interval=budget.monitor_active_interval(),
            warn_pct=budget.monitor_warn_pct(),
            critical_pct=budget.monitor_critical_pct(),
        ) as monitor:
            with Dashboard(
                monitor,
                max_log_lines=budget.dashboard_log_lines(),
                refresh_rate=budget.dashboard_refresh_rate(),
            ) as dash:

                # --- Stage 1: Merge (with inline rdflib validation) ---
                chunks = sorted(merged_dir.glob("europeana_*.ttl"))
                if state.is_complete("merge"):
                    dash.log("Merge already complete (from checkpoint)")
                    dash.complete_stage()
                elif skip_merge and chunks:
                    dash.log(f"Skipping merge ({len(chunks)} chunks already exist)")
                    state.mark_complete("merge")
                    dash.complete_stage()
                else:
                    dash.set_stage("Merge", total=None)
                    dash.log("Scanning prefixes from sample…")
                    prefixes = scan_prefixes_from_sample(ttl_dir)

                    # Resume: skip ZIPs already processed in a prior run
                    merge_stage = state.get_stage("merge")
                    skip_zips = frozenset(merge_stage.processed_zips)

                    # Update stage with actual total after prefix scan
                    all_zips = sorted(ttl_dir.glob("*.zip"))
                    remaining = len(all_zips) - len(skip_zips)
                    dash.set_stage("Merge", total=remaining)

                    merge_result = merge_ttl(
                        ttl_dir, merged_dir,
                        chunk_size_gb=chunk_size, workers=workers, prefixes=prefixes,
                        monitor=monitor, skip_zips=skip_zips,
                        dashboard=dash,
                        copy_buf_size=budget.copy_buf_size(),
                        backpressure_thresholds=budget.backpressure_thresholds(),
                        backpressure_sleeps=budget.backpressure_sleeps(),
                        cpu_target=budget.cpu_target_pct(),
                        cpu_low=budget.cpu_low_pct(),
                        throttle_consecutive_samples=budget.throttle_consecutive_samples(),
                        writer_join_timeout=budget.writer_join_timeout(),
                        checksum_policy=checksum_policy,
                    )
                    state.update_merge(merge_result)
                    state.save(state_path)
                    dash.complete_stage()

                    if merge_result.failed_zips:
                        msg = (
                            f"Merge: {len(merge_result.failed_zips)} ZIP(s) failed "
                            f"({merge_result.error_rate:.1%} error rate)"
                        )
                        dash.log(msg)
                        log.warning(msg)
                        failures.append(msg)

                # --- Stage 2: Write Qleverfile ---
                if not state.is_complete("write_qleverfile"):
                    dash.set_stage("Qleverfile")
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
                    dash.complete_stage()
                else:
                    dash.log("Qleverfile already written (from checkpoint)")
                    dash.complete_stage()

                # --- Stage 3: Index ---
                index_exists = any(index_dir.glob("europeana.index.*"))
                if state.is_complete("index"):
                    dash.log("Index already built (from checkpoint)")
                    dash.complete_stage()
                elif skip_index and index_exists:
                    dash.log(f"Skipping index (files exist in {index_dir})")
                    state.mark_complete("index")
                    state.save(state_path)
                    dash.complete_stage()
                else:
                    dash.set_stage("Index")
                    ctx.invoke(index, qlever_args=())
                    state.mark_complete("index")
                    state.save(state_path)
                    dash.complete_stage()

                # --- Stage 4: Start server ---
                dash.set_stage("Start")
                ctx.invoke(start)
                server_started = True
                dash.complete_stage()

                # --- Stage 5: Export ---
                registry = ExportRegistry()
                exports = registry.for_set("pipeline")
                dash.set_stage("Export", total=len(exports))

                export_result = ExportPipeline(
                    output_dir=exports_dir,
                    exports=exports,
                    qlever_url=f"http://localhost:{port}",
                    timeout=timeout,
                    skip_existing=True,
                    memory_limit=duckdb_memory,
                    duckdb_threads=budget.duckdb_threads(),
                    temp_directory=exports_dir / ".duckdb_tmp",
                    dashboard=dash,
                    http_chunk_size=budget.http_chunk_size(),
                    http_connect_timeout=budget.http_connect_timeout(),
                    duckdb_sample_size=budget.duckdb_sample_size(),
                    duckdb_row_group_size=budget.duckdb_row_group_size(),
                    max_retries=budget.export_max_retries(),
                    retry_delays=budget.export_retry_delays(),
                ).run()
                state.update_export(export_result)
                state.save(state_path)
                dash.complete_stage()

                if export_result.failed:
                    for name, err in export_result.failed.items():
                        failures.append(f"Export {name}: {err}")

    except KeyboardInterrupt:
        log.info("Pipeline interrupted by user")
        state.save(state_path)
        display.console.print("\n[yellow]Pipeline interrupted. Progress saved — resume with the same command.[/yellow]")
        raise SystemExit(130)
    except Exception as exc:
        log.exception("Pipeline failed")
        state.mark_failed("pipeline", str(exc))
        state.save(state_path)
        raise
    finally:
        # Always stop server if we started it
        if server_started:
            try:
                display.console.rule("[bold cyan]Stop Server[/bold cyan]")
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
