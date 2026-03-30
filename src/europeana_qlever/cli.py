"""Click CLI for the Europeana EDM → QLever → Parquet pipeline.

Install & run::

    cd ~/dev/europeana-qlever
    uv sync
    uv run europeana-qlever --help

Or for a single command::

    uv run europeana-qlever -d ~/europeana merge /data/TTL --workers 12
    uv run europeana-qlever -d ~/europeana export -q core_metadata
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
    from .query import QueryBuilder

    builder = QueryBuilder()
    examples = [
        ("geolocated_places", builder.geolocated_places()),
        ("iiif_availability", builder.iiif_availability()),
        ("items_by_country", builder.items_by_country()),
        ("items_by_language", builder.items_by_language()),
        ("items_by_provider", builder.items_by_provider()),
        ("items_by_type", builder.items_by_type()),
        ("items_by_type_and_country", builder.items_by_type_and_country()),
        ("items_by_type_and_language", builder.items_by_type_and_language()),
        ("items_by_year", builder.items_by_year()),
        ("mime_type_distribution", builder.mime_type_distribution()),
        ("text_genre_distribution", builder.text_genre_distribution()),
    ]

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
        # Normalize indentation: QueryBuilder output has PREFIX lines at col 0
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
@click.pass_context
def start(ctx: click.Context):
    """Start the QLever SPARQL server (wraps `qlever start`).

    Runs from <work-dir>/index/. If a server is already running on the
    configured port, it is stopped first.
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
        ("Component queries (base tables for composite exports)", qb.all_component_queries()),
        ("AI dataset queries", qb.all_ai_queries()),
        ("Analytics queries", qb.all_analytics_queries()),
    ]:
        table = Table(title=category)
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="dim")
        table.add_column("Description")
        for name, spec in queries.items():
            qtype = "composite" if spec.is_composite else "SPARQL"
            table.add_row(name, qtype, qb.describe(name))
        display.console.print(table)
        display.console.print()


# ---------------------------------------------------------------------------
# Shared query resolution helper
# ---------------------------------------------------------------------------

def _resolve_queries(
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
    limit: int | None = None,
):
    """Build a QueryBuilder and resolve the queries dict from CLI args.

    Returns ``(qb, queries)`` where *qb* is a :class:`QueryBuilder` and
    *queries* is ``dict[str, QuerySpec]`` mapping names to query specs.
    """
    from .query import QueryBuilder, QueryFilters, QuerySpec

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
        if not (modes == 1 or (bool(query_names) and modes == 1)):
            raise click.UsageError(
                "Cannot combine --all, -q, --query-set, and .sparql files."
            )

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
    queries: dict[str, QuerySpec] = {}

    if sparql_files:
        for p in sparql_files:
            stem = p.stem
            name = re.sub(r"^\d+_", "", stem)
            queries[name] = QuerySpec(name=name, sparql=p.read_text())
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
        # Check if any requested name is in the registry (handles composites)
        all_specs = qb.all_queries(filters)
        for name in query_names:
            if name in all_specs:
                queries[name] = all_specs[name]
            else:
                method = getattr(qb, name, None)
                if method is None or name.startswith("_") or name.startswith("all_"):
                    raise click.UsageError(
                        f"Unknown query: '{name}'. Use `list-queries` to see available queries."
                    )
                if name == "entity_links":
                    sparql = method(filters=filters)
                else:
                    sparql = method(filters)
                queries[name] = QuerySpec(name=name, sparql=sparql)

    return qb, queries


def _analysis_output_path(
    analysis_dir: Path,
    suffix: str,
    output_path: Path | None,
    query_names: tuple[str, ...],
    query_set: str | None,
    run_all: bool,
    sparql_files: tuple[Path, ...],
    queries: dict[str, str],
) -> Path:
    """Derive the output path for an analysis report."""
    if output_path:
        return output_path
    if query_names and len(query_names) == 1:
        stem = query_names[0]
    elif query_set:
        stem = query_set
    elif run_all:
        stem = "base"
    elif sparql_files:
        stem = "_".join(p.stem for p in sparql_files)
    else:
        stem = "_".join(sorted(queries))
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
@click.argument("sparql_files", nargs=-1,
                type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--all", "run_all", is_flag=True, default=False,
              help="Analyze all base queries.")
@click.option("-q", "--query", "query_names", multiple=True,
              help="Named query from QueryBuilder (repeatable).")
@click.option("--query-set", type=click.Choice(["base", "ai", "analytics", "all"]),
              help="Analyze a predefined set of queries.")
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
    limit: int,
    send: int,
    output_path: Path | None,
    qlever_url: str,
    timeout: int,
):
    """Profile queries against a running QLever server.

    Runs queries with a LIMIT, collects runtime information from the
    QLever execution tree, and writes a Markdown report identifying
    bottlenecks.  The report is designed to be pasted into a Claude Code
    prompt for further diagnosis.
    """
    from .analysis import analyze_all, render_markdown

    qb, specs = _resolve_queries(
        sparql_files, run_all, query_names, query_set,
        countries, types, rights_category, providers,
        min_completeness, year_from, year_to, filter_languages,
        dataset_names,
    )

    # Extract SPARQL strings, skipping composite queries
    queries = {n: s.sparql for n, s in specs.items() if s.sparql is not None}
    skipped = [n for n, s in specs.items() if s.is_composite]
    if skipped:
        display.console.print(
            f"[dim]Skipping composite queries (no SPARQL): {', '.join(skipped)}[/dim]"
        )

    analysis_dir: Path = ctx.obj["analysis_dir"]
    out = _analysis_output_path(
        analysis_dir, "qlever", output_path,
        query_names, query_set, run_all, sparql_files, queries,
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    results = analyze_all(
        queries, qlever_url, timeout,
        send=send, limit=limit, describe_fn=qb.describe,
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
@click.argument("sparql_files", nargs=-1,
                type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--all", "run_all", is_flag=True, default=False,
              help="Analyze all base queries.")
@click.option("-q", "--query", "query_names", multiple=True,
              help="Named query from QueryBuilder (repeatable).")
@click.option("--query-set", type=click.Choice(["base", "ai", "analytics", "all"]),
              help="Analyze a predefined set of queries.")
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
              help="Additional language(s) for label resolution. Repeatable.")
@click.option("--dataset-name", "dataset_names", multiple=True,
              help="Filter by datasetName (repeatable).")
@click.option("-o", "--output", "output_path", type=click.Path(path_type=Path),
              default=None, help="Output Markdown file (default: analysis/<name>.static.md).")
@click.pass_context
def analyze_static(
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
    output_path: Path | None,
):
    """Offline structural analysis of SPARQL query complexity.

    Parses queries into SPARQL algebra and identifies structural
    bottlenecks (deep OPTIONAL nesting, high variable count, expensive
    aggregations) without requiring a running QLever server.
    """
    from .analysis import render_static_markdown, static_analyze_all

    qb, specs = _resolve_queries(
        sparql_files, run_all, query_names, query_set,
        countries, types, rights_category, providers,
        min_completeness, year_from, year_to, filter_languages,
        dataset_names,
    )

    # Extract SPARQL strings, skipping composite queries
    queries = {n: s.sparql for n, s in specs.items() if s.sparql is not None}
    skipped = [n for n, s in specs.items() if s.is_composite]
    if skipped:
        display.console.print(
            f"[dim]Skipping composite queries (no SPARQL): {', '.join(skipped)}[/dim]"
        )

    analysis_dir: Path = ctx.obj["analysis_dir"]
    out = _analysis_output_path(
        analysis_dir, "static", output_path,
        query_names, query_set, run_all, sparql_files, queries,
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    results = static_analyze_all(queries, describe_fn=qb.describe)

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
@click.option("--timeout", default=QLEVER_QUERY_TIMEOUT, show_default=True,
              help="Per-query timeout in seconds.")
@click.option("--skip-existing", is_flag=True, default=False,
              help="Skip queries whose .parquet already exists.")
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
    duckdb_memory: str,
    keep_base: bool,
    reuse_tsv: bool,
):
    """Export SPARQL query results from QLever as Parquet files.

    Use --all for base queries, --query-set for a category, -q for
    specific named queries, or pass .sparql file paths directly.
    Filter options (--country, --type, etc.) apply to named queries.

    Composite queries (like items_enriched) automatically export their
    dependencies first, then compose the final Parquet via DuckDB.
    Use --no-keep-base to clean up intermediate base table files.
    """
    from .export import export_all

    _qb, queries = _resolve_queries(
        sparql_files, run_all, query_names, query_set,
        countries, types, rights_category, providers,
        min_completeness, year_from, year_to, filter_languages,
        dataset_names, limit=limit,
    )

    exports_dir: Path = ctx.obj["exports_dir"]

    budget = ctx.obj["budget"]

    # Resolve DuckDB memory
    if duckdb_memory == "auto":
        duckdb_memory = budget.duckdb_memory()

    result = export_all(
        output_dir=exports_dir,
        queries=queries,
        qlever_url=qlever_url,
        timeout=timeout,
        skip_existing=skip_existing,
        memory_limit=duckdb_memory,
        temp_directory=exports_dir / ".duckdb_tmp",
        keep_base=keep_base,
        reuse_tsv=reuse_tsv,
        http_chunk_size=budget.http_chunk_size(),
        http_connect_timeout=budget.http_connect_timeout(),
        duckdb_sample_size=budget.duckdb_sample_size(),
        duckdb_row_group_size=budget.duckdb_row_group_size(),
        max_retries=budget.export_max_retries(),
        retry_delays=budget.export_retry_delays(),
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
                qb = QueryBuilder()
                queries = qb.all_base_queries()
                # Total for dashboard: count SPARQL queries only
                # (composite dependencies are handled automatically)
                dash.set_stage("Export", total=len(queries))

                export_result = export_all(
                    output_dir=exports_dir,
                    queries=queries,
                    qlever_url=f"http://localhost:{port}",
                    timeout=timeout,
                    skip_existing=True,
                    memory_limit=duckdb_memory,
                    temp_directory=exports_dir / ".duckdb_tmp",
                    dashboard=dash,
                    http_chunk_size=budget.http_chunk_size(),
                    http_connect_timeout=budget.http_connect_timeout(),
                    duckdb_sample_size=budget.duckdb_sample_size(),
                    duckdb_row_group_size=budget.duckdb_row_group_size(),
                    max_retries=budget.export_max_retries(),
                    retry_delays=budget.export_retry_delays(),
                )
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
