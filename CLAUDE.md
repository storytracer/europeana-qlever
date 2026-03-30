# CLAUDE.md — europeana-qlever

## What this project is

A Python CLI (`europeana-qlever`) that ingests the full Europeana EDM metadata dump (~66M records, 2–5B triples in Turtle) into a QLever SPARQL engine and exports query results as Parquet files. The pipeline: download TTL ZIPs from Europeana FTP → merge into chunked TTL → build QLever index → serve SPARQL endpoint → export to Parquet via DuckDB.

## Tech stack

- **Python 3.11+**, managed with **uv** (not pip)
- **click** for CLI, **rich** for progress/output, **rdflib** for RDF parsing, **httpx** for streaming HTTP, **duckdb** for Parquet conversion, **pyarrow**, **psutil** for resource monitoring
- **QLever** as the SPARQL engine (C++, compiled from source or installed natively)
- Build system: **hatchling**

## Project layout

```
pyproject.toml                    # Package metadata, dependencies, entry point
src/europeana_qlever/
  __init__.py                     # Package version
  cli.py                          # Click command definitions (all commands)
  constants.py                    # EDM namespaces, QLever settings, rights URIs, throttle/monitor thresholds
  dashboard.py                    # Live Rich dashboard (system resources, pipeline progress, log tail)
  analysis.py                     # Query performance analysis (QLever runtime info → Markdown report)
  display.py                      # Terminal output helpers (console setup, formatting)
  export.py                       # QLever HTTP streaming + DuckDB Parquet conversion
  merge.py                        # Parallel TTL extraction, inline validation, prefix discovery
  monitor.py                      # Background resource monitor (CPU, memory, disk, process tracking)
  query.py                        # Dynamic SPARQL query generator (QueryBuilder, QueryFilters)
  resources.py                    # Auto-detection of system resources & budget calculation
  state.py                        # Pipeline state tracking, ValidateResult dataclass, logging setup
  throttle.py                     # Adaptive concurrency throttle (CPU/memory-aware, replaces semaphore)
  validate.py                     # Standalone validation + inline entry validation for merge
tests/
  test_analysis.py                # Query performance analysis tests
  test_export.py                  # Export functionality tests
  test_query.py                   # Unit tests for query generation
  test_state.py                   # State persistence tests
  test_throttle.py                # Adaptive throttle tests
  test_validate.py                # Validation tests
EDM.md                            # Europeana Data Model reference (EDM, entities, rights)
README.md                         # General-purpose project README
```

Note: source lives under `src/europeana_qlever/` (src layout), mapped in `pyproject.toml` via `[tool.hatch.build.targets.wheel] packages = ["src/europeana_qlever"]`.

### Work directory layout (not in repo)

All output lives under a single work directory specified via `-d` / `--work-dir` (or `EUROPEANA_QLEVER_WORK_DIR` env var). Subdirectory names are defined in `constants.py`.

| Subdirectory | Constant | Purpose |
|--------------|----------|---------|
| `ttl-merged/` | `MERGED_SUBDIR` | Merged chunk TTL files (~5 GB each) |
| `index/` | `INDEX_SUBDIR` | Qleverfile, settings.json, QLever index files |
| `exports/` | `EXPORTS_SUBDIR` | Parquet output files (TSV intermediates are deleted) |
| `monitor.log` | — | CSV resource monitor log (RSS, available memory, disk free) |

The source TTL ZIP directory is user-managed and passed as a positional argument to `merge` and `scan-prefixes`.

## Commands to know

```bash
uv sync                                                         # Install dependencies
uv run europeana-qlever --help                                   # Show all CLI commands
uv run europeana-qlever -d WORK_DIR merge TTL_DIR                # Merge TTL ZIPs into chunks
uv run europeana-qlever -d WORK_DIR validate TTL_DIR             # Read-only pre-flight validation
uv run europeana-qlever -d WORK_DIR write-qleverfile             # Generate Qleverfile + settings.json
uv run europeana-qlever -d WORK_DIR index                        # Build QLever index
uv run europeana-qlever -d WORK_DIR start                        # Start SPARQL server on :7001
uv run europeana-qlever -d WORK_DIR stop                         # Stop SPARQL server
uv run europeana-qlever -d WORK_DIR list-queries                 # List all 36 available queries
uv run europeana-qlever -d WORK_DIR analyze -q items_enriched    # Analyze query performance
uv run europeana-qlever -d WORK_DIR analyze --query-set ai       # Analyze all AI queries
uv run europeana-qlever -d WORK_DIR export --all                 # Export all base queries to Parquet
uv run europeana-qlever -d WORK_DIR export --query-set all       # Export all 36 queries
uv run europeana-qlever -d WORK_DIR export -q items_enriched     # Export a specific named query
uv run europeana-qlever -d WORK_DIR export FILE.sparql           # Export a custom .sparql file
uv run europeana-qlever -d WORK_DIR pipeline TTL_DIR             # Run full pipeline end-to-end
uv run pytest tests/test_query.py                                # Run query generator tests
```

All commands require `-d WORK_DIR` (or `EUROPEANA_QLEVER_WORK_DIR` env var). Output paths are derived automatically. Always use `uv run` — never bare `python` or `pip install`.

## Architecture notes

- **Merge** is I/O-bound: uses `ProcessPoolExecutor` for parallel ZIP extraction. Workers stream line-by-line from ZIP entries to temp files on disk — never holding more than one line in memory — then a writer thread copies temp files into chunked output files in 1 MB reads. An `AdaptiveThrottle` (see below) dynamically bounds in-flight work based on CPU and memory pressure. Per-file `@prefix`/`@base` lines are stripped and replaced with a unified prefix header per chunk. Temp files live in `output_dir/.merge_tmp/` and are cleaned up automatically. Each ZIP entry is validated inline via rdflib parsing — invalid entries are skipped and logged. Graceful shutdown with explicit writer thread join timeouts.
- **Adaptive throttle** (`throttle.py`): `AdaptiveThrottle` replaces the old fixed `threading.Semaphore` for merge concurrency control. Starts at `max(4, workers // 2)` permits, scales between `min_permits` (2) and `max_permits` (workers) based on system CPU and memory pressure. Uses hysteresis (default 3 consecutive samples above/below thresholds) to avoid jitter. Default targets: scale down above 85% CPU or memory, scale up below 65% CPU / 70% memory. Step sizes: 2 down, 1 up. Chained into `ResourceMonitor`'s sample callback so every monitor tick triggers an adjustment check. Fires an `on_adjust` callback for live dashboard updates.
- **Validation** (`validate.py`): Provides both standalone validation (`validate` CLI command — read-only pre-flight check with rdflib parsing and optional checksum verification) and inline entry validation used during merge. `validate_entry()` parses individual TTL entries with rdflib; `validate_all()` orchestrates full validation of a TTL directory.
- **MD5 checksums** are skipped by default (`--checksum-policy=skip`) because the Europeana FTP md5sum files are unreliable. Of ~2,300 md5sum files tested (March 2026), only 7% match their companion ZIPs. The FTP server appears to regenerate md5sum files from freshly built ZIPs that are never actually published (stale checksums), and also strips leading zeros from hex hashes (126 files affected). The `validate` command's `--no-checksums` flag and the merge/pipeline `--checksum-policy` option control this behavior.
- **Prefix discovery** samples ~50 ZIPs via rdflib to catch non-standard prefixes. Falls back to regex if rdflib fails on a file. The canonical EDM prefix set is in `constants.py` as `EDM_PREFIXES`.
- **Export** streams multi-GB SPARQL results via httpx (chunked reads, never loaded into memory), writes TSV, converts to Parquet with DuckDB (`zstd` compression, explicit `memory_limit="4GB"`, spill-to-disk via `temp_directory`), then deletes the intermediate TSV.
- **Resource monitoring** (`monitor.py`): `ResourceMonitor` runs as a daemon thread, sampling process RSS, system available memory, disk free space, and CPU usage (system-wide and per-process including children). Samples are logged to `monitor.log` (CSV format). Console warnings fire on state transitions at 80% (warn) and 90% (critical) system memory usage. The monitor supports active/idle modes (1s vs 2s sampling interval) — switched to active during merge. `ResourceSnapshot` dataclass includes `cpu_pct`, `process_cpu_pct`, `process_rss_mb`, and `child_count` fields. Thresholds are configurable in `constants.py`.
- **Resource budgeting** (`resources.py`): Auto-detects system resources (CPU count, memory, disk) and computes resource budgets for merge workers, throttle targets, and writer timeouts. All parameters are overridable via CLI or constants.
- **Dashboard** (`dashboard.py`): Live Rich-based terminal dashboard showing real-time system resources (CPU, memory, disk with threshold-based coloring), pipeline stage progress, and a scrolling log tail. Auto-refreshes based on monitor samples. Redirects console output to log panel to prevent flickering.
- **State tracking** (`state.py`): Pipeline state persistence, `ValidateResult` dataclass for validation outcomes, and logging setup.
- **Query generation** (`query.py`) uses `QueryBuilder` to dynamically generate SPARQL queries from composable fragments. `QueryFilters` dataclass carries filter parameters (country, type, rights category, year range, etc.). Queries are grouped into base (7), AI dataset (5), and analytics (24) categories — 36 total. The builder produces `dict[str, str]` consumed by `export_all()`.
- **Qleverfile generation** supports both native (compiled from source) and Docker modes. Native is preferred for performance. Memory settings are computed dynamically from available RAM by `ResourceBudget`: query memory 45%, cache 15%, cache single entry 7.5%, stxxl 25% — all relative to available memory with no hard caps (only minimum floors). Thread count is set to half of CPU count. The `write-qleverfile` command accepts `--query-memory`, `--cache-size`, and `--stxxl-memory` overrides.
- **Pipeline** (`pipeline` command) runs all stages end-to-end: merge → write-qleverfile → index → start → export → stop. Supports `--skip-merge` and `--skip-index` flags. The entire pipeline runs inside a `ResourceMonitor` context for continuous resource tracking.
- Export queries are generated by `QueryBuilder` in `query.py`. The `export --all` flag runs all base queries; `--query-set` runs a category; `-q` runs individual named queries. Custom `.sparql` file paths can also be passed.

## Europeana EDM domain context

For comprehensive documentation on the Europeana Data Model, entity relationships, RDF namespaces, and rights framework, see `EDM.md`. Use it as the primary reference for any questions about the EDM or Europeana at large.

The data follows the **Europeana Data Model (EDM)**. Key entities:

- **ProvidedCHO** — the cultural heritage object
- **ore:Proxy** — descriptive metadata (there's a provider proxy and a Europeana proxy per item)
- **ore:Aggregation** — links to digital representations (WebResources)
- **edm:Agent**, **edm:Place**, **skos:Concept**, **edm:TimeSpan** — contextual entities

The provider proxy (identified by `FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" }`) holds the primary descriptive metadata (dc:title, dc:creator, etc.). The Europeana proxy (`edm:europeanaProxy "true"`) holds normalised enrichments (edm:year).

### QueryBuilder and QueryFilters

`QueryBuilder` generates all SPARQL queries via composable fragment methods (`_provider_proxy()`, `_aggregation()`, `_rights_category_bind()`, etc.). `QueryFilters` is a dataclass with optional filter fields (countries, types, rights_category, year_from/to, limit, etc.) that are injected as FILTER clauses. Rights URIs are classified into "open", "restricted", and "permission" categories using STRSTARTS/CONTAINS patterns in the `_rights_category_bind()` fragment. Constants for rights URI lists and labels live in `constants.py`.

**Language resolution** uses a parallel English + vernacular model. Item-level properties (dc:title, dc:description) produce separate English and vernacular columns plus a COALESCE-resolved fallback. The vernacular language is bound from `dc:language` on the provider proxy. Entity labels (skos:prefLabel) use a simpler chain: en → user extras → any. Users add languages via `QueryBuilder(languages=[...])` or the `--language` CLI flag, which produces extra output columns. Base queries expose only the resolved column; AI queries expose all parallel columns.

## Conventions

- All data-processing logic is in the Python CLI. No bash scripts for pipeline steps.
- CLI commands are in `cli.py`, business logic in `merge.py`/`export.py`/`query.py`/`validate.py`/`throttle.py`, configuration in `constants.py`, resource detection in `resources.py`, live display in `dashboard.py`/`display.py`, state tracking in `state.py`.
- Use `rich.console.Console` for all terminal output (not bare `print`).
- Click options use `Path` type with `path_type=Path`.
