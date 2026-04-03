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
  export.py                       # Export types (Export, QueryExport, CompositeExport), ExportRegistry, ExportPipeline
  merge.py                        # Parallel TTL extraction, inline validation, prefix discovery
  monitor.py                      # Background resource monitor (CPU, memory, disk, process tracking)
  query.py                        # SPARQL query generation (Query, QueryFilters, QueryRegistry, SparqlHelpers)
  resources.py                    # Auto-detection of system resources & budget calculation
  state.py                        # Pipeline state tracking, ValidateResult dataclass, logging setup
  throttle.py                     # Adaptive concurrency throttle (CPU/memory-aware, replaces semaphore)
  validate.py                     # Standalone validation + inline entry validation for merge
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
uv run europeana-qlever -d WORK_DIR list-exports                 # List all available exports
uv run europeana-qlever -d WORK_DIR analyze qlever items_core    # Runtime analysis against QLever
uv run europeana-qlever -d WORK_DIR analyze static items_core    # Offline structural analysis
uv run europeana-qlever -d WORK_DIR analyze static --set summary # Analyze all summary exports
uv run europeana-qlever -d WORK_DIR export --all                 # Export all pipeline exports to Parquet
uv run europeana-qlever -d WORK_DIR export --set all             # Export everything
uv run europeana-qlever -d WORK_DIR export items_enriched        # Export a specific named export
uv run europeana-qlever -d WORK_DIR pipeline TTL_DIR             # Run full pipeline end-to-end
```

All commands require `-d WORK_DIR` (or `EUROPEANA_QLEVER_WORK_DIR` env var). Output paths are derived automatically. Always use `uv run` — never bare `python` or `pip install`.

## Architecture notes

- **Merge** is I/O-bound: uses `ProcessPoolExecutor` for parallel ZIP extraction. Workers stream line-by-line from ZIP entries to temp files on disk — never holding more than one line in memory — then a writer thread copies temp files into chunked output files in 1 MB reads. An `AdaptiveThrottle` (see below) dynamically bounds in-flight work based on CPU and memory pressure. Per-file `@prefix`/`@base` lines are stripped and replaced with a unified prefix header per chunk. Temp files live in `output_dir/.merge_tmp/` and are cleaned up automatically. Each ZIP entry is validated inline via rdflib parsing — invalid entries are skipped and logged. Graceful shutdown with explicit writer thread join timeouts.
- **Adaptive throttle** (`throttle.py`): `AdaptiveThrottle` replaces the old fixed `threading.Semaphore` for merge concurrency control. Starts at `max(4, workers // 2)` permits, scales between `min_permits` (2) and `max_permits` (workers) based on system CPU and memory pressure. Uses hysteresis (default 3 consecutive samples above/below thresholds) to avoid jitter. Default targets: scale down above 85% CPU or memory, scale up below 65% CPU / 70% memory. Step sizes: 2 down, 2 up. Chained into `ResourceMonitor`'s sample callback so every monitor tick triggers an adjustment check. Fires an `on_adjust` callback for live dashboard updates.
- **Validation** (`validate.py`): Provides both standalone validation (`validate` CLI command — read-only pre-flight check with rdflib parsing and optional checksum verification) and inline entry validation used during merge. `validate_entry()` parses individual TTL entries with rdflib; `validate_all()` orchestrates full validation of a TTL directory.
- **MD5 checksums** are skipped by default (`--checksum-policy=skip`) because the Europeana FTP md5sum files are unreliable. Of ~2,300 md5sum files tested (March 2026), only 7% match their companion ZIPs. The FTP server appears to regenerate md5sum files from freshly built ZIPs that are never actually published (stale checksums), and also strips leading zeros from hex hashes (126 files affected). The `validate` command's `--no-checksums` flag and the merge/pipeline `--checksum-policy` option control this behavior.
- **Prefix discovery** samples ~50 ZIPs via rdflib to catch non-standard prefixes. Falls back to regex if rdflib fails on a file. The canonical EDM prefix set is in `constants.py` as `EDM_PREFIXES`.
- **Hybrid export pipeline** uses a two-phase architecture. **Phase 1** (`QueryExport`) exports simple, flat SPARQL scans to Parquet "base tables" (no GROUP BY, no GROUP_CONCAT, minimal OPTIONALs). **Phase 2** (`CompositeExport`) uses DuckDB SQL (`compose.py`) to join the base table Parquet files, resolve language priorities, aggregate multi-valued properties, and produce final denormalized exports. This splits the workload: QLever does what it's best at (index scans, triple pattern matching over 5B triples) while DuckDB does the heavy lifting (columnar aggregation, GROUP BY, JOINs over Parquet). `CompositeExport` objects hold a list of `ComposeStep` objects executed sequentially with per-step progress logging, and transparently trigger their dependencies. The `--keep-base / --no-keep-base` flag controls whether intermediate base table Parquets are retained. TSV→Parquet conversion strips `?` prefixes from QLever column headers for clean column names.
- **Export (Phase 1)** streams multi-GB SPARQL results via httpx (chunked reads, never loaded into memory), writes TSV, then converts to Parquet via `tsv_to_parquet()` using parallel rdflib parsing (`ProcessPoolExecutor`) and PyArrow with `zstd` compression. The parallel conversion uses bounded submission (at most `workers * 2` in-flight futures) to keep memory constant regardless of file size — this is critical for large exports like `items_subjects` (258M rows, 27 GB TSV). DuckDB memory budget for Phase 2 composition is 75% of available RAM (min 4 GB, no upper cap).
- **Resource monitoring** (`monitor.py`): `ResourceMonitor` runs as a daemon thread, sampling process RSS, system available memory, disk free space, and CPU usage (system-wide and per-process including children). Samples are logged to `monitor.log` (CSV format). Console warnings fire on state transitions at 80% (warn) and 90% (critical) system memory usage. The monitor supports active/idle modes (1s vs 2s sampling interval) — switched to active during merge. `ResourceSnapshot` dataclass includes `cpu_pct`, `process_cpu_pct`, `process_rss_mb`, and `child_count` fields. Thresholds are configurable in `constants.py`.
- **Resource budgeting** (`resources.py`): Auto-detects system resources (CPU count, memory, disk) and computes resource budgets for merge workers, throttle targets, and writer timeouts. All parameters are overridable via CLI or constants.
- **Dashboard** (`dashboard.py`): Live Rich-based terminal dashboard showing real-time system resources (CPU, memory, disk with threshold-based coloring), pipeline stage progress, and a scrolling log tail. Auto-refreshes based on monitor samples. Redirects console output to log panel to prevent flickering.
- **State tracking** (`state.py`): Pipeline state persistence, `ValidateResult` dataclass for validation outcomes, and logging setup.
- **Query generation** (`query.py`) uses `QueryRegistry` to build `Query` objects that generate SPARQL on demand via composable fragment helpers (`SparqlHelpers`). `QueryFilters` carries filter parameters (country, type, reuse level, year range, etc.) and knows how to express itself as SPARQL (`to_sparql()`, `limit_clause()`). There are 26 SPARQL queries. `ExportRegistry` (`export.py`) wraps each `Query` in a `QueryExport` and adds `CompositeExport` objects. Exports are grouped into named `ExportSet`s: pipeline (14), summary (13), items, entities, rights.
- **Query analysis** (`analysis.py`) has two modes: `analyze qlever` sends queries to a running QLever server with `Accept: application/qlever-results+json` and `send=0` to get execution tree metadata without result transfer; `analyze static` uses rdflib's SPARQL algebra (`parseQuery` + `translateQuery`) to identify structural complexity (OPTIONAL nesting depth, triple pattern count, aggregate cost, variable fan-out) without executing queries. Both produce Markdown reports in the `analysis/` subdirectory.
- **Qleverfile generation** supports both native (compiled from source) and Docker modes. Native is preferred for performance. Memory settings are computed dynamically from available RAM by `ResourceBudget`: query memory 45%, cache 15%, cache single entry 7.5%, stxxl 25% — all relative to available memory with no hard caps (only minimum floors). Thread count is set to half of CPU count. The `write-qleverfile` command accepts `--query-memory`, `--cache-size`, and `--stxxl-memory` overrides.
- **Pipeline** (`pipeline` command) runs all stages end-to-end: merge → write-qleverfile → index → start → export → stop. Progress is checkpointed to `pipeline_state.json` so a failed or interrupted run resumes automatically; `--force` clears the checkpoint. Supports `--skip-merge` and `--skip-index` flags. The entire pipeline runs inside a `ResourceMonitor` + `Dashboard` context for continuous resource tracking and live terminal display.
- **Composition SQL** (`compose.py`) generates DuckDB SQL templates as `ComposeStep` objects (12 steps for `items_enriched` via `ComposeStep.items_enriched_steps()`). Templates use `{exports_dir}` as a placeholder replaced at execution time. The flagship enriched export composes 8 component tables + agents, with multi-valued property aggregation using native Parquet types (`LIST<VARCHAR>` for subjects/dates/years/languages, `LIST<STRUCT<name VARCHAR, uri VARCHAR>>` for creators), and creator label resolution via agent entity join. The final step is marked `is_final=True` for COPY-to-Parquet wrapping.
- **Export execution** is orchestrated by `ExportPipeline` (`export.py`). The `export --all` flag runs the pipeline export set; `--set` runs a named set; positional arguments select individual exports by name (composites like `items_enriched` transparently trigger dependencies). The `--keep-base / --no-keep-base` flag controls cleanup of intermediate component table Parquets.

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

### Query, Export, and Filter types

**`Query`** (`query.py`) represents a named SPARQL query with a `sparql(filters)` method that generates query text on demand. `QueryRegistry` builds all 26 queries at construction time. `SparqlHelpers` provides reusable EDM triple pattern fragments.

**`QueryFilters`** carries optional filter parameters (countries, types, reuse_level, year_from/to, limit, etc.) and expresses itself as SPARQL via `to_sparql()` and `limit_clause()`. Rights URIs are classified into "open", "restricted", and "prohibited" reuse levels using pattern matching in `rights.py`.

**`Export`** (`export.py`) is the base class for anything producing a Parquet file. `QueryExport` wraps a `Query` with a frozen SPARQL string. `CompositeExport` holds `ComposeStep` objects and a `depends_on` list. `ExportRegistry` builds all exports (26 query-based + 1 composite). `ExportPipeline` executes exports in dependency order.

**`ExportSet`** (`export.py`) is a named, non-exclusive collection of export names. Built-in sets: `pipeline` (14 exports), `summary` (13), `items`, `entities`, `rights`. Accessible via `--set` CLI flag.

**Component exports** (`items_core`, `items_titles`, `items_descriptions`, `items_subjects`, `items_dates`, `items_languages`, `items_years`, `items_creators`) are flat SPARQL scans with no GROUP BY that serve as building blocks for `items_enriched`. Available individually as positional args, e.g. `export items_core`.

**Multi-valued columns** in `items_enriched` use native Parquet types: `LIST<VARCHAR>` for subjects, dates, years, and languages; `LIST<STRUCT<name VARCHAR, uri VARCHAR>>` for creators (pairing each resolved display name with its entity URI, or NULL for literal-string creators).

## Conventions

- All data-processing logic is in the Python CLI. No bash scripts for pipeline steps.
- CLI commands are in `cli.py`, business logic in `merge.py`/`export.py`/`query.py`/`validate.py`/`throttle.py`, configuration in `constants.py`, resource detection in `resources.py`, live display in `dashboard.py`/`display.py`, state tracking in `state.py`.
- **No unit tests.** This project does not use unit tests. Do not create test files or run pytest.
- Use `rich.console.Console` for all terminal output (not bare `print`).
- Click options use `Path` type with `path_type=Path`.
