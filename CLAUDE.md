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
  analysis.py                     # Query performance analysis: runtime (QLever) and static (SPARQL algebra)
  display.py                      # Terminal output helpers (console setup, formatting)
  compose.py                      # DuckDB composition SQL for hybrid SPARQL/DuckDB pipeline
  export.py                       # QLever HTTP streaming + DuckDB Parquet conversion + hybrid pipeline
  merge.py                        # Parallel TTL extraction, inline validation, prefix discovery
  monitor.py                      # Background resource monitor (CPU, memory, disk, process tracking)
  query.py                        # Dynamic SPARQL query generator (QueryBuilder, QueryFilters, QuerySpec)
  resources.py                    # Auto-detection of system resources & budget calculation
  state.py                        # Pipeline state tracking, ValidateResult dataclass, logging setup
  throttle.py                     # Adaptive concurrency throttle (CPU/memory-aware, replaces semaphore)
  validate.py                     # Standalone validation + inline entry validation for merge
tests/
  test_analysis.py                # Query performance analysis tests
  test_compose.py                 # DuckDB composition SQL tests
  test_export.py                  # Export functionality tests (including ?-stripping)
  test_query.py                   # Unit tests for query generation and QuerySpec
  test_state.py                   # State persistence tests
  test_throttle.py                # Adaptive throttle tests
  test_validate.py                # Validation tests
EDM.md                            # Europeana Data Model reference (EDM, entities, rights)
README.md                         # General-purpose project README
docs/
  qlever/docs/                    # QLever documentation (MkDocs source from upstream)
    quickstart.md, qleverfile.md, qlever-control.md, text-search.md,
    geosparql.md, path-search.md, materialized-views.md, benchmarks.md,
    compliance.md, troubleshooting.md, faq.md, rebuild-index.md, update.md, ...
  europeana/                      # Europeana Knowledge Base (scraped from Europeana docs)
    Europeana Knowledge Base/
      EDM - Mapping guidelines/   # EDM class/property mapping guides (ProvidedCHO, Aggregation, WebResource, contextual classes)
      Publishing guide/           # Content/metadata tiers, rights statements, digital objects
      Terminology.md, Media policy.md, Semantic enrichments.md, APIs Documentation.md, ...
```

Note: source lives under `src/europeana_qlever/` (src layout), mapped in `pyproject.toml` via `[tool.hatch.build.targets.wheel] packages = ["src/europeana_qlever"]`.

### Work directory layout (not in repo)

All output lives under a single work directory specified via `-d` / `--work-dir` (or `EUROPEANA_QLEVER_WORK_DIR` env var). Subdirectory names are defined in `constants.py`.

| Subdirectory | Constant | Purpose |
|--------------|----------|---------|
| `ttl-merged/` | `MERGED_SUBDIR` | Merged chunk TTL files (~5 GB each) |
| `index/` | `INDEX_SUBDIR` | Qleverfile, settings.json, QLever index files |
| `exports/` | `EXPORTS_SUBDIR` | Parquet output files (TSV intermediates are deleted) |
| `analysis/` | `ANALYSIS_SUBDIR` | Query performance analysis Markdown reports |
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
uv run europeana-qlever -d WORK_DIR list-queries                 # List all 18 available queries
uv run europeana-qlever -d WORK_DIR analyze qlever -q items_enriched  # Runtime analysis against QLever
uv run europeana-qlever -d WORK_DIR analyze static -q items_enriched  # Offline structural analysis
uv run europeana-qlever -d WORK_DIR analyze static --query-set ai     # Analyze all AI queries
uv run europeana-qlever -d WORK_DIR export --all                 # Export all base queries to Parquet
uv run europeana-qlever -d WORK_DIR export --query-set all       # Export all 18 queries
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
- **Hybrid export pipeline** uses a two-phase architecture. **Phase 1** exports simple, flat SPARQL scans to Parquet "base tables" (no GROUP BY, no GROUP_CONCAT, minimal OPTIONALs). **Phase 2** uses DuckDB SQL (`compose.py`) to join the base table Parquet files, resolve language priorities, aggregate multi-valued properties, and produce final denormalized exports. This splits the workload: QLever does what it's best at (index scans, triple pattern matching over 5B triples) while DuckDB does the heavy lifting (columnar aggregation, GROUP BY, JOINs over Parquet). Composite exports like `items_enriched` are specified via `QuerySpec.compose_sql` and transparently trigger their dependencies. The `--keep-base / --no-keep-base` flag controls whether intermediate base table Parquets are retained. TSV→Parquet conversion strips `?` prefixes from QLever column headers for clean column names.
- **Export (Phase 1)** streams multi-GB SPARQL results via httpx (chunked reads, never loaded into memory), writes TSV, converts to Parquet with DuckDB (`zstd` compression, spill-to-disk via `temp_directory`), then deletes the intermediate TSV. DuckDB memory budget is 30% of available RAM (4–16 GB range).
- **Resource monitoring** (`monitor.py`): `ResourceMonitor` runs as a daemon thread, sampling process RSS, system available memory, disk free space, and CPU usage (system-wide and per-process including children). Samples are logged to `monitor.log` (CSV format). Console warnings fire on state transitions at 80% (warn) and 90% (critical) system memory usage. The monitor supports active/idle modes (1s vs 2s sampling interval) — switched to active during merge. `ResourceSnapshot` dataclass includes `cpu_pct`, `process_cpu_pct`, `process_rss_mb`, and `child_count` fields. Thresholds are configurable in `constants.py`.
- **Resource budgeting** (`resources.py`): Auto-detects system resources (CPU count, memory, disk) and computes resource budgets for merge workers, throttle targets, and writer timeouts. All parameters are overridable via CLI or constants.
- **Dashboard** (`dashboard.py`): Live Rich-based terminal dashboard showing real-time system resources (CPU, memory, disk with threshold-based coloring), pipeline stage progress, and a scrolling log tail. Auto-refreshes based on monitor samples. Redirects console output to log panel to prevent flickering.
- **State tracking** (`state.py`): Pipeline state persistence, `ValidateResult` dataclass for validation outcomes, and logging setup.
- **Query generation** (`query.py`) uses `QueryBuilder` to dynamically generate SPARQL queries from composable fragments. `QueryFilters` dataclass carries filter parameters (country, type, rights category, year range, etc.). `QuerySpec` dataclass wraps each query with metadata: `sparql` (for simple exports), `compose_sql` (for composite DuckDB exports), `depends_on` (dependency list), and `description`. Queries are grouped into base (6), component (8), AI dataset (1), and example (11) categories — 18 user-facing queries plus 8 component building blocks. The builder's registry methods return `dict[str, QuerySpec]` consumed by `export_all()`.
- **Query analysis** (`analysis.py`) has two modes: `analyze qlever` sends queries to a running QLever server with `Accept: application/qlever-results+json` and `send=0` to get execution tree metadata without result transfer; `analyze static` uses rdflib's SPARQL algebra (`parseQuery` + `translateQuery`) to identify structural complexity (OPTIONAL nesting depth, triple pattern count, aggregate cost, variable fan-out) without executing queries. Both produce Markdown reports in the `analysis/` subdirectory.
- **Qleverfile generation** supports both native (compiled from source) and Docker modes. Native is preferred for performance. Memory settings are computed dynamically from available RAM by `ResourceBudget`: query memory 45%, cache 15%, cache single entry 7.5%, stxxl 25% — all relative to available memory with no hard caps (only minimum floors). Thread count is set to half of CPU count. The `write-qleverfile` command accepts `--query-memory`, `--cache-size`, and `--stxxl-memory` overrides.
- **Pipeline** (`pipeline` command) runs all stages end-to-end: merge → write-qleverfile → index → start → export → stop. Supports `--skip-merge` and `--skip-index` flags. The entire pipeline runs inside a `ResourceMonitor` context for continuous resource tracking.
- **Composition SQL** (`compose.py`) generates DuckDB SQL templates for composite exports. Templates use `{exports_dir}` as a placeholder replaced at execution time. `items_enriched_sql()` composes the flagship AI dataset from 8 component tables + agents, with language resolution (en → vernacular → extras → any), multi-valued property aggregation (`STRING_AGG`), and creator label resolution via agent entity join.
- Export queries are generated by `QueryBuilder` in `query.py`. The `export --all` flag runs all base queries; `--query-set` runs a category; `-q` runs individual named queries (composites like `items_enriched` transparently export dependencies first). Custom `.sparql` file paths can also be passed. The `--keep-base / --no-keep-base` flag controls cleanup of intermediate component table Parquets.

## Documentation

Local documentation is available in three locations — always read from these local copies rather than fetching from the web:

- **`EDM.md`** — Europeana Data Model reference (entity relationships, RDF namespaces, rights framework). Primary quick-reference for EDM questions.
- **`docs/qlever/docs/`** — Full QLever documentation (upstream MkDocs source). Covers Qleverfile format, SPARQL compliance, text/geo/path search, materialized views, benchmarks, troubleshooting, and more. Read these when working on index configuration, Qleverfile generation, query features, or debugging QLever behavior.
- **`docs/europeana/Europeana Knowledge Base/`** — Europeana's knowledge base. Includes EDM mapping guidelines (per-class property documentation for ProvidedCHO, Aggregation, WebResource, contextual classes), publishing guides (content/metadata tiers, rights statements), semantic enrichments, API docs, terminology, and media policy. Read these for detailed EDM field semantics, data quality rules, or Europeana-specific conventions beyond what `EDM.md` covers.

## Europeana EDM domain context

For comprehensive documentation on the Europeana Data Model, entity relationships, RDF namespaces, and rights framework, see `EDM.md`. For detailed per-class property documentation and mapping guidelines, see `docs/europeana/Europeana Knowledge Base/EDM - Mapping guidelines/`. For QLever engine internals and configuration, see `docs/qlever/docs/`.

The data follows the **Europeana Data Model (EDM)**. Key entities:

- **ProvidedCHO** — the cultural heritage object
- **ore:Proxy** — descriptive metadata (there's a provider proxy and a Europeana proxy per item)
- **ore:Aggregation** — links to digital representations (WebResources)
- **edm:Agent**, **edm:Place**, **skos:Concept**, **edm:TimeSpan** — contextual entities

The provider proxy (identified by `FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" }`) holds the primary descriptive metadata (dc:title, dc:creator, etc.). The Europeana proxy (`edm:europeanaProxy "true"`) holds normalised enrichments (edm:year).

### QueryBuilder, QueryFilters, and QuerySpec

`QueryBuilder` generates all SPARQL queries via composable fragment methods (`_provider_proxy()`, `_aggregation()`, `_rights_category_bind()`, etc.). `QueryFilters` is a dataclass with optional filter fields (countries, types, rights_category, year_from/to, limit, etc.) that are injected as FILTER clauses. Rights URIs are classified into "open", "restricted", and "permission" categories using STRSTARTS/CONTAINS patterns in the `_rights_category_bind()` fragment. Constants for rights URI lists and labels live in `constants.py`.

`QuerySpec` wraps each export with: `name`, `sparql` (for simple SPARQL exports), `compose_sql` (for DuckDB composite exports), `depends_on` (list of dependency names), and `description`. The `is_composite` property distinguishes the two types. Registry methods (`all_base_queries()`, `all_ai_queries()`, etc.) return `dict[str, QuerySpec]`.

**Component queries** (`items_core`, `items_titles`, `items_descriptions`, `items_subjects`, `items_dates`, `items_languages`, `items_years`, `items_creators`) are flat SPARQL scans with no GROUP BY that serve as building blocks for composite exports. They're available via `all_component_queries()` and individually via `-q items_core`, etc.

**Language resolution** uses a parallel English + vernacular model. For simple SPARQL exports, item-level properties (dc:title, dc:description) produce separate English and vernacular columns plus a COALESCE-resolved fallback. For composite exports, language resolution moves to DuckDB: the component tables export raw values with language tags, and the composition SQL applies FILTER/COALESCE logic. Entity labels (skos:prefLabel) use a simpler chain: en → user extras → any. Users add languages via `QueryBuilder(languages=[...])` or the `--language` CLI flag.

## Conventions

- All data-processing logic is in the Python CLI. No bash scripts for pipeline steps.
- CLI commands are in `cli.py`, business logic in `merge.py`/`export.py`/`query.py`/`validate.py`/`throttle.py`, configuration in `constants.py`, resource detection in `resources.py`, live display in `dashboard.py`/`display.py`, state tracking in `state.py`.
- Use `rich.console.Console` for all terminal output (not bare `print`).
- Click options use `Path` type with `path_type=Path`.
