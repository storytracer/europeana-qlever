# CLAUDE.md — europeana-qlever

## What this project is

A Python CLI (`europeana-qlever`) that ingests the full Europeana EDM metadata dump (~66M records, 2–5B triples in Turtle) into a QLever SPARQL engine and exports query results as Parquet files. The pipeline: download TTL ZIPs from Europeana FTP → merge into chunked TTL → build QLever index → serve SPARQL endpoint → export to Parquet via DuckDB.

A companion **GRASP** integration (`grasp/`) enables natural-language querying of the Europeana knowledge graph via an LLM-powered agent (NL → SPARQL). GRASP connects to the same QLever endpoint and is benchmarked with a suite of 50+ test questions.

## Tech stack

- **Python 3.11+**, managed with **uv** (not pip)
- **click** for CLI, **rich** for progress/output, **rdflib** for RDF parsing, **httpx** for streaming HTTP, **duckdb** for Parquet conversion, **pyarrow**, **psutil** for resource monitoring, **linkml-runtime** for schema-driven metadata
- **QLever** as the SPARQL engine (C++, compiled from source or installed natively)
- Build system: **hatchling**

## Project layout

```
pyproject.toml                    # Package metadata, dependencies, entry point
src/europeana_qlever/
  __init__.py                     # Package version
  cli.py                          # Click command definitions (all commands)
  constants.py                    # QLever settings, directory layout, throttle/monitor thresholds
  schema_loader.py                # Schema loader: programmatic access to LinkML schema (prefixes, attributes, export discovery, PyArrow schemas)
  schema/
    __init__.py                   # Package marker
    edm.yaml                      # EDM base schema — primary source of truth for the EDM data model (12 classes, 242 fully-described attributes)
    edm_parquet.yaml              # Export schema — imports edm.yaml, declares all 38 export tables (values_*, links_*, group_items, map_*, explorer_*) as LinkML classes with SPARQL patterns and pipeline annotations
  dashboard.py                    # Live Rich dashboard (system resources, pipeline progress, log tail)
  analysis.py                     # Query performance analysis: runtime (QLever) and static (SPARQL algebra)
  display.py                      # Terminal output helpers (console setup, formatting)
  compose.py                      # DuckDB composition SQL for group_items / map_* composites (ComposeStep)
  export.py                       # Export types (Export, QueryExport, CompositeExport), ExportRegistry, ExportPipeline
  merge.py                        # Parallel TTL extraction, inline validation, prefix discovery
  report.py                       # Composable report: YAML-driven questions (static SQL + ask agent), ReportFilters
  report_questions/                # Bundled report question YAML files (read directly by `report`)
    __init__.py                    # Package marker + DEFAULTS_DIR path
    overview.yml                   # Overview / quality scan
    external_links.yml             # External link / sameAs analysis
  monitor.py                      # Background resource monitor (CPU, memory, disk, process tracking)
  query.py                        # Schema-driven SPARQL query generation (Query, QueryFilters, QueryRegistry, SparqlHelpers)
  resources.py                    # Auto-detection of system resources & budget calculation
  rights.py                       # Rights statement registry: reuse level classification, SPARQL/DuckDB generators for rights families and labels
  state.py                        # Pipeline state tracking, ValidateResult dataclass, logging setup
  telemetry.py                    # Structured JSONL telemetry (command spans, resource samples, stage events)
  throttle.py                     # Adaptive concurrency throttle (CPU/memory-aware, replaces semaphore)
  validate.py                     # Standalone validation + inline entry validation for merge
  croissant.py                     # Croissant (JSON-LD) metadata generation for exported Parquet files
  ask/                             # NL querying package (unified interface for Parquet + SPARQL backends)
    __init__.py                    # AskBackend ABC, AskResult, AskStep, display helpers
    parquet.py                     # AskParquet — NL→DuckDB agent (OpenAI function calling, offline)
    sparql.py                      # AskSPARQL — NL→SPARQL agent (GRASP WebSocket, requires servers)
    notes.py                       # Structured EDM domain knowledge (renders for DuckDB + SPARQL)
    store.py                       # ParquetStore — shared DuckDB engine over Parquet files
    benchmark.py                   # Unified benchmark runner (any AskBackend over test questions)
    benchmark.yml                  # Test questions for NL-to-SPARQL/SQL evaluation (10 questions)
  explorer/                        # Browser-based DuckDB explorer (server + bundled SPA)
    __init__.py                    # static_dir() helper
    server.py                      # ExplorerEngine + threaded HTTP server with /api/* JSON endpoints
    static/                        # Single-page app (Preact + htm + Chart.js, all vendored offline)
      index.html, app.js, style.css
      vendor/                      # preact.mjs, hooks.mjs, htm.mjs, chart.umd.min.js
  grasp/                           # GRASP resource files (package data, shipped with code)
    __init__.py                    # Resource path helpers
    prefixes.json                  # RDF namespace mappings for entity/property search
    europeana-entity.sparql        # SPARQL for extracting entity labels during index setup
    europeana-property.sparql      # SPARQL for extracting property URIs during index setup
    entities-info.sparql           # Runtime entity detail lookup template
    properties-info.sparql         # Runtime property detail lookup template
README.md                         # General-purpose project README
scripts/
  update-all.py                   # uv script: orchestrator — runs all update-*.py in dependency order
  update-edm-schema.py            # uv script: regenerate schema/edm.yaml from ontology sources (XSD, OWL, external RDF)
  update-metis-vocabularies.py    # uv script: sync Europeana's Metis vocabulary registry
  update-qlever-docs.py           # uv script: sync QLever docs from upstream GitHub repo
  update-europeana-docs.py        # uv script: sync Europeana KB from Confluence (anonymous, incremental)
references/                       # Vendored upstream specification artifacts (ontologies + URI registries)
  ontologies/
    metis-schema/                 # Europeana metis-schema XSD + OWL files (copied from GitHub clone)
    external/                     # Cached external ontology files (DC, DCTERMS, SKOS, FOAF, ORE, etc.)
  vocabularies/
    metis-vocabularies/           # Europeana's Metis vocabulary registry — authority URI patterns + XSL mappings
docs/
  qlever/docs/                    # QLever documentation (MkDocs source from upstream)
    quickstart.md, qleverfile.md, qlever-control.md, text-search.md,
    geosparql.md, path-search.md, materialized-views.md, benchmarks.md,
    compliance.md, troubleshooting.md, faq.md, rebuild-index.md, update.md, ...
  europeana/                      # Europeana Knowledge Base (exported from Confluence)
    EDM.md                         # Europeana Data Model reference — narrative overview of EDM entities, namespaces, rights
    confluence-lock.json           # CME lockfile for incremental updates (tracks page versions)
    Europeana Knowledge Base/
      Europeana Knowledge Base.md                        # Space homepage / index
      Article 14 National Implementations Overview/      # Country-specific Article 14 implementations
      Copyright management guidelines for .../           # Copyright guidance for cultural heritage institutions
      EDM - Mapping guidelines/                          # EDM class/property mapping (ProvidedCHO, Aggregation, WebResource, contextual classes)
      Europeana and IIIF/                                # IIIF integration documentation
      Europeana APIs Documentation/                      # API suite (Search, Record, IIIF, OAI-PMH)
      Europeana Data Model/                              # EDM specification details
      Organisation entities in Europeana/                # Organisation management (Zoho CRM, entity pages)
      Out of commerce works National Implementations Overview/  # Country-specific out-of-commerce implementations
      Persistent identifiers/                            # PID standards and aggregator roles
      Publishing guide/                                  # Content/metadata tiers, rights statements, digital objects
      Publishing guide for 3D content/                   # 3D-specific publishing requirements
      Semantic enrichments/                              # Automatic enrichment workflows and vocabulary support
      User Guides & Training/                            # Training materials, Metis sandbox guide
      Terminology.md, Media policy.md, FAQs on digital cultural heritage..., ...
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
| `reports/` | — | Report output (JSON + Markdown) |
| `telemetry.jsonl` | — | Structured JSONL telemetry log (command spans, resource samples, stage events) |

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
uv run europeana-qlever -d WORK_DIR list-exports                 # List all exports (use --all-partitions for per-property link scans)
uv run europeana-qlever -d WORK_DIR analyze qlever values_ore_Proxy  # Runtime analysis against QLever
uv run europeana-qlever -d WORK_DIR analyze static values_ore_Proxy  # Offline structural analysis
uv run europeana-qlever -d WORK_DIR analyze static --set raw     # Analyze all raw (values_* + links_*) exports
uv run europeana-qlever -d WORK_DIR export --all                 # Export all pipeline exports to Parquet
uv run europeana-qlever -d WORK_DIR export --set raw             # Export all raw values_* / links_* tables
uv run europeana-qlever -d WORK_DIR export group_items           # Export the fast-analytics per-CHO scalar table (dependencies auto-exported)
uv run europeana-qlever -d WORK_DIR export links_ore_Proxy --property dc_subject  # Re-run a single link partition
uv run europeana-qlever -d WORK_DIR pipeline TTL_DIR             # Run full pipeline end-to-end
uv run europeana-qlever -d WORK_DIR report                       # Run composable report (all sections)
uv run europeana-qlever -d WORK_DIR report -s volume,rights      # Run specific sections
uv run europeana-qlever -d WORK_DIR report -q total_items        # Run specific questions
uv run europeana-qlever -d WORK_DIR report -f "country=NL,FR"    # Filtered report (any schema field)
uv run europeana-qlever -d WORK_DIR report --probe-urls          # Include live URL reachability probing
uv run europeana-qlever -d WORK_DIR report -v                    # Verbose: show agent traces for NL questions
uv run europeana-qlever -d WORK_DIR create-views                 # Create QLever materialized views (requires running server)
uv run europeana-qlever -d WORK_DIR ask "How many open items?"   # NL→DuckDB: ask questions about Parquet exports
uv run europeana-qlever -d WORK_DIR ask --backend sparql "How many open items?"  # NL→SPARQL via GRASP
uv run europeana-qlever -d WORK_DIR ask -f "type=IMAGE" "Resolution distribution?"  # With pre-filter
uv run europeana-qlever -d WORK_DIR ask -v "Top 10 subjects?"   # Verbose: show agent trace
uv run europeana-qlever -d WORK_DIR benchmark                    # Run all benchmark questions (parquet)
uv run europeana-qlever -d WORK_DIR benchmark --backend both     # Compare parquet vs SPARQL
uv run europeana-qlever -d WORK_DIR benchmark --question 5       # Run single question
uv run europeana-qlever -d WORK_DIR explore                      # Launch browser-based DuckDB explorer (port 1378)
uv run europeana-qlever -d WORK_DIR explore --no-open            # Same, but don't auto-open browser
uv run europeana-qlever -d WORK_DIR explore --data-url URL       # Point explorer at a remote Parquet (e.g. HuggingFace)
```

All commands require `-d WORK_DIR` (or `EUROPEANA_QLEVER_WORK_DIR` env var). Output paths are derived automatically. Always use `uv run` — never bare `python` or `pip install`.

### GRASP commands

GRASP is an external NL→SPARQL agent (`grasp` CLI, installed via `uv tool install grasp`). It is managed by the CLI just like QLever — configuration is generated into `{work_dir}/grasp/`, resources are bundled in `src/europeana_qlever/grasp/`.

```bash
# Generate GRASP config (creates {work_dir}/grasp/europeana-grasp.yaml + notes)
uv run europeana-qlever -d WORK_DIR write-grasp-config

# Build GRASP search indices from QLever (requires QLever running on :7001)
uv run europeana-qlever -d WORK_DIR grasp-setup

# Start/stop GRASP server
uv run europeana-qlever -d WORK_DIR grasp-start
uv run europeana-qlever -d WORK_DIR grasp-stop

# Ask via GRASP (requires GRASP + QLever running)
uv run europeana-qlever -d WORK_DIR ask --backend sparql "How many open items?"
```

## Architecture notes

- **Merge** is I/O-bound: uses `ProcessPoolExecutor` for parallel ZIP extraction. Workers stream line-by-line from ZIP entries to temp files on disk — never holding more than one line in memory — then a writer thread copies temp files into chunked output files in 1 MB reads. An `AdaptiveThrottle` (see below) dynamically bounds in-flight work based on CPU and memory pressure. Per-file `@prefix`/`@base` lines are stripped and replaced with a unified prefix header per chunk. Temp files live in `output_dir/.merge_tmp/` and are cleaned up automatically. Each ZIP entry is validated inline via rdflib parsing — invalid entries are skipped and logged. Graceful shutdown with explicit writer thread join timeouts.
- **Adaptive throttle** (`throttle.py`): `AdaptiveThrottle` replaces the old fixed `threading.Semaphore` for merge concurrency control. Starts at `max(4, workers // 2)` permits, scales between `min_permits` (2) and `max_permits` (workers) based on system CPU and memory pressure. Uses hysteresis (default 3 consecutive samples above/below thresholds) to avoid jitter. Default targets: scale down above 85% CPU or memory, scale up below 65% CPU / 70% memory. Step sizes: 2 down, 2 up. Chained into `ResourceMonitor`'s sample callback so every monitor tick triggers an adjustment check. Fires an `on_adjust` callback for live dashboard updates.
- **Validation** (`validate.py`): Provides both standalone validation (`validate` CLI command — read-only pre-flight check with rdflib parsing and optional checksum verification) and inline entry validation used during merge. `validate_entry()` parses individual TTL entries with rdflib; `validate_all()` orchestrates full validation of a TTL directory.
- **MD5 checksums** are skipped by default (`--checksum-policy=skip`) because the Europeana FTP md5sum files are unreliable. Of ~2,300 md5sum files tested (March 2026), only 7% match their companion ZIPs. The FTP server appears to regenerate md5sum files from freshly built ZIPs that are never actually published (stale checksums), and also strips leading zeros from hex hashes (126 files affected). The `validate` command's `--no-checksums` flag and the merge/pipeline `--checksum-policy` option control this behavior.
- **Prefix discovery** samples ~50 ZIPs via rdflib to catch non-standard prefixes. Falls back to regex if rdflib fails on a file. The canonical EDM prefix set is derived from the LinkML schema via `edm_schema.prefixes()`.
- **Hybrid export pipeline** uses a two-phase architecture aligned with EDM class boundaries. **Phase 1** (`QueryExport`) exports two kinds of raw SPARQL scans: `values_*` tables are wide, one row per entity, carrying only scalar k_/v_ columns; `links_*` tables are long, one row per value, written as Hive-partitioned directories (`<table>/x_property=<col>/data.parquet`) with one partition per link property. All scans are flat (no GROUP BY, no GROUP_CONCAT, minimal OPTIONALs). **Phase 2** (`CompositeExport`) uses DuckDB SQL (`compose.py`) to join the raw Parquets and produce `group_items` (scalar-only per-CHO summary) plus the `map_*` lookup tables. This splits the workload: QLever does index scans and triple pattern matching over ~2–5 B triples while DuckDB does the heavy lifting (columnar aggregation, GROUP BY, JOINs over Parquet). `CompositeExport` objects hold a list of `ComposeStep` objects executed sequentially with per-step progress logging, and transparently trigger their dependencies. For `links_*` tables, `CompositeExport` is a no-op aggregator whose only job is to depend on every per-property partition scan. Multi-valued descriptive metadata (titles, subjects, creators, …) stays in the raw `links_ore_Proxy` Hive directory rather than being denormalized — a previous `merged_items` table that forced 1:1 LIST\<STRUCT\> flattening per CHO was removed because the join tree did not fit in memory on the full 60 M-CHO dataset. TSV→Parquet conversion strips `?` prefixes from QLever column headers for clean column names.
- **Export (Phase 1)** streams multi-GB SPARQL results via httpx (chunked reads, never loaded into memory), writes TSV, then converts to Parquet via `tsv_to_parquet()` using parallel rdflib parsing (`ProcessPoolExecutor`) and PyArrow with `zstd` compression. The parallel conversion uses bounded submission (at most `workers * 2` in-flight futures) to keep memory constant regardless of file size — this is critical for the largest per-property link scans (e.g. `links_ore_Proxy__dc_subject`, hundreds of millions of rows). Link partition scans write directly into the parent table's Hive layout; readers see the directory as a single logical table via DuckDB's `hive_partitioning=true`. DuckDB memory budget for Phase 2 composition is 75% of available RAM (min 4 GB, no upper cap).
- **Resource monitoring** (`monitor.py`): `ResourceMonitor` runs as a daemon thread, sampling process RSS, system available memory, disk free space, and CPU usage (system-wide and per-process including children). Samples are emitted as `resource_sample` events via the telemetry system (see below). Console warnings fire on state transitions at 80% (warn) and 90% (critical) system memory usage, also emitted as `warning` telemetry events. The monitor supports active/idle modes (1s vs 2s sampling interval) — switched to active during merge. `ResourceSnapshot` dataclass includes `cpu_pct`, `process_cpu_pct`, `process_rss_mb`, and `child_count` fields. Thresholds are configurable in `constants.py`.
- **Resource budgeting** (`resources.py`): Auto-detects system resources (CPU count, memory, disk) and computes resource budgets for merge workers, throttle targets, and writer timeouts. All parameters are overridable via CLI or constants.
- **Dashboard** (`dashboard.py`): Live Rich-based terminal dashboard showing real-time system resources (CPU, memory, disk with threshold-based coloring), pipeline stage progress, and a scrolling log tail. Auto-refreshes based on monitor samples. Redirects console output to log panel to prevent flickering.
- **Telemetry** (`telemetry.py`): Unified structured JSONL logging system. `TelemetryRecorder` appends one JSON object per line to `telemetry.jsonl` in the work directory. Events include `command_start`/`command_end` (with wall_seconds, peak_rss_mb, counters), `resource_sample` (from monitor), `stage_start`/`stage_end` (from pipeline state), and `warning` (from monitor transitions). `NullTelemetryRecorder` is a no-op for when telemetry is disabled. The `command_span` context manager wraps CLI commands to emit start/end events with timing and resource usage. Replaces the old CSV `monitor.log` approach.
- **State tracking** (`state.py`): Pipeline state persistence, `ValidateResult` dataclass for validation outcomes, and logging setup. Emits `stage_start`/`stage_end` telemetry events on state transitions via an optional `TelemetryRecorder` set with `set_telemetry()`.
- **Query generation** (`query.py`) uses `QueryRegistry` to build `Query` objects that generate SPARQL on demand via composable fragment helpers (`SparqlHelpers`). Every query is derived from the LinkML schema (`edm_parquet.yaml`): one `values_<Class>` query per EDM class (scalar k_/v_ columns) plus one `links_<Class>__<property>` query per link property (the synthetic per-partition scans that feed the Hive-partitioned `links_*` tables). `QueryFilters` carries filter parameters (country, type, reuse level, year range, etc.) and knows how to express itself as SPARQL (`to_sparql()`, `limit_clause()`). `ExportRegistry` (`export.py`) wraps each `Query` in a `QueryExport`, groups partition scans into no-op `CompositeExport`s for the parent `links_*` tables, and adds composite exports for `group_items`, the `map_*` lookups, and the `explorer_*` derived tables. Exports are grouped into named `ExportSet`s driven by schema `export_sets` annotations: `pipeline` (38, all final exports), `raw` (26 — values_* + links_*), `group` (1), `maps` (5 — `map_rights`, `map_sameAs`, `map_cho_entities`, `map_edm_entities`, `map_cho_mimetypes`), `explorer` (everything the browser explorer needs).
- **Query analysis** (`analysis.py`) has two modes: `analyze qlever` sends queries to a running QLever server with `Accept: application/qlever-results+json` and `send=0` to get execution tree metadata without result transfer; `analyze static` uses rdflib's SPARQL algebra (`parseQuery` + `translateQuery`) to identify structural complexity (OPTIONAL nesting depth, triple pattern count, aggregate cost, variable fan-out) without executing queries. Both produce Markdown reports in the `analysis/` subdirectory.
- **Qleverfile generation** supports both native (compiled from source) and Docker modes. Native is preferred for performance. Memory settings are computed dynamically from available RAM by `ResourceBudget`: query memory 45%, cache 15%, cache single entry 7.5%, stxxl 25% — all relative to available memory with no hard caps (only minimum floors). Thread count is set to half of CPU count. The `write-qleverfile` command accepts `--query-memory`, `--cache-size`, and `--stxxl-memory` overrides.
- **Pipeline** (`pipeline` command) runs all stages end-to-end: merge → write-qleverfile → index → start → create-views → export → stop. Progress is checkpointed to `pipeline_state.json` so a failed or interrupted run resumes automatically; `--force` clears the checkpoint. Supports `--skip-merge` and `--skip-index` flags. The entire pipeline runs inside a `ResourceMonitor` + `Dashboard` context for continuous resource tracking and live terminal display.
- **Composition SQL** (`compose.py`) generates DuckDB SQL templates as `ComposeStep` objects, derived from the LinkML schema and dispatched per composite table by `compose_steps_for(name)`: `group_items`, `map_rights`, `map_sameAs`, `map_cho_entities`, `map_edm_entities`, `map_cho_mimetypes`, plus the `explorer_*` derived tables (`explorer_edm_entities`, `explorer_concepts`, `explorer_agents`, `explorer_places`, `explorer_timespans`, `explorer_facet_top_n`). Steps read raw `values_*` / `links_*` Parquet files via the `{exports_dir}` placeholder (replaced at execution time); `_links_read(...)` wraps a Hive-partitioned links directory as a single logical table. Rights SQL comes from `rights.py` (`duckdb_family_case`, `duckdb_is_open_case`, `duckdb_label_case`). The final step of each composite is marked `is_final=True` for COPY-to-Parquet wrapping.
- **Export execution** is orchestrated by `ExportPipeline` (`export.py`). The `export --all` flag runs the `pipeline` export set; `--set` runs a named set; positional arguments select individual exports by name (composites like `group_items` transparently trigger dependencies). `--property` lets you re-run a single partition of a Hive-partitioned `links_*` table. The `--keep-base / --no-keep-base` flag controls cleanup of intermediate raw Parquets after composition.
- **Explorer** (`explorer/` + `explore` CLI command): A browser-based, server-backed DuckDB explorer over `group_items.parquet`. The bundled single-page app (`static/`, built with Preact + htm + Chart.js, all vendored under `static/vendor/` for fully offline use) talks to a small threaded `http.server` (`server.py`) that exposes JSON `POST /api/{schema,summary,top-values,sample,labels}` endpoints answered by `ExplorerEngine` against a shared DuckDB connection. Facet selections combine semantically as AND, and the `explorer_facet_top_n` precomputed table backs the top-values facet cache for fast initial rendering. IRI labels are resolved on demand via the `explorer_*` entity tables (organizations, agents, places, concepts, timespans) plus a CHO-title view that joins through `values_ore_Proxy`. The `explore` command kills any prior listener on the fixed `EXPLORER_PORT` (constants.py: 1378), opens the browser, and runs until Ctrl+C. Use `--data-url` to point at a remote Parquet (e.g. a HuggingFace URL) instead of the local file.
- **GRASP integration**: [GRASP](https://github.com/ad-freiburg/grasp) is an external LLM-powered NL-to-SPARQL agent, managed by the CLI like QLever. Resource files (SPARQL templates, prefix mappings) are bundled in `src/europeana_qlever/grasp/` as package data. Runtime config (`europeana-grasp.yaml`, `europeana-notes.json`) is generated into `{work_dir}/grasp/` by `write-grasp-config`. The domain notes are generated from `ask/notes.py`'s `export_grasp_notes()` — structured EDM knowledge rendered for SPARQL. `grasp-setup` replaces the old `setup.sh` — downloads entity labels and property URIs from QLever, builds fuzzy/embedding search indices, installs info query templates, and creates materialized views. `grasp-start`/`grasp-stop` manage the GRASP server process. The SPARQL backend (`ask/sparql.py`) wraps the GRASP WebSocket protocol (`ws://localhost:6789/live`) as an `AskBackend` implementation, enabling unified querying and benchmarking across both backends.
- **Materialized views** (`create-views` command): The `open-items` QLever materialized view precomputes all items with open reuse rights (CC0, PDM, CC-BY, CC-BY-SA) joined with their `edm:type`. The SPARQL is generated from `rights.py`'s `sparql_reuse_level_filter("open")`. GRASP queries use `SERVICE view:open-items { ... }` syntax for instant indexed lookups instead of expensive `STRSTARTS(STR(?rights), ...)` filters. A second optional `sample-items` view holds N ProvidedCHO IRIs (created via `create-views --sample-size N`) and powers `export --sample-size` for coherent end-to-end smoke tests. Both are created by the `create-views` CLI command (also run automatically by `pipeline` after server start) and stored persistently by QLever. View name constants: `VIEW_OPEN_ITEMS`, `VIEW_SAMPLE_ITEMS` in `constants.py`.
- **Report** (`report.py`): Composable report system driven by the YAML question files bundled in the `report_questions/` package directory. The shipped sections are `overview.yml` (volume / rights / providers / languages / content / media scan) and `external_links.yml` (sameAs link well-formedness and Metis-recognition). Each YAML file defines a section with questions. Questions with a `query` field execute as static DuckDB SQL (fast, deterministic); questions without a `query` are answered by the ask agent (`AskParquet` or `AskSPARQL`). The bundled YAMLs are read directly — to add or modify questions, edit them in `src/europeana_qlever/report_questions/`. `ReportFilters` is a schema-driven filter class that accepts any Item field name and generates DuckDB WHERE clauses using `filterable_fields()`. The `report` command supports `--sections/-s` and `--questions/-q` for composability, `--filters/-f` for data scoping, and `--verbose/-v` for agent traces. Output is JSON + Markdown in `{work_dir}/reports/`. URL liveness probing is retained as an optional special section (`--probe-urls`). The command is interruptible — Ctrl+C cleanly stops the run after the in-flight question.
- **Croissant metadata** (`croissant.py`): Generates a `croissant.json` (JSON-LD) file alongside exported Parquets using the `mlcroissant` library. Describes all tables, columns, types, and descriptions — all derived from the LinkML schema (`edm_parquet.yaml`). Includes SHA-256 checksums and file sizes. Auto-generated at the end of `ExportPipeline.run()`.
- **NL querying** (`ask/`): Unified package for natural-language querying with pluggable backends. `AskBackend` (ABC in `__init__.py`) defines the interface; `AskResult` and `AskStep` are the shared result types. Two implementations: `AskParquet` (`parquet.py`) translates NL→DuckDB SQL via OpenAI function calling over exported Parquet files (offline, no servers); `AskSPARQL` (`sparql.py`) translates NL→SPARQL via GRASP WebSocket (requires running QLever + GRASP). `ParquetStore` (`store.py`) is the shared DuckDB engine — registers all Parquets as views, applies `ReportFilters` to `group_items`, creates an `orgs` convenience view. Used by both `ask` and `report`. `EdmNote` (`notes.py`) provides structured domain knowledge renderable for both DuckDB (`render_duckdb_notes()`) and SPARQL (`render_sparql_notes()`, `export_grasp_notes()`). `Benchmark` (`benchmark.py`) runs test questions from `benchmark.yml` through any backend with grading, skip/retry, and JSONL output. The `ask` CLI command selects backend with `--backend parquet|sparql`; the `benchmark` command supports `--backend parquet|sparql|both`.
- **GRASP resources** (`grasp/` package in src): Bundles static resource files for the GRASP server (SPARQL templates, prefix mappings) as package data. Runtime configuration (`europeana-grasp.yaml`, `europeana-notes.json`, search indices) is generated into `{work_dir}/grasp/` by `write-grasp-config` and `grasp-setup` CLI commands. The GRASP server lifecycle is managed by `grasp-start`/`grasp-stop`, mirroring the QLever `start`/`stop` pattern.

## Documentation

### EDM data model reference

The primary sources of truth for the Europeana Data Model are:

- **`schema/edm.yaml`** — Machine-readable LinkML schema with all 12 EDM classes and 242 attributes. Every attribute has a description (sourced from the EDM OWL ontology, metis-schema XSD annotations, and upstream vocabulary ontologies). This is the authoritative reference for class/property structure, cardinality, ranges, and namespaces. Read this first for any EDM property question.
- **`docs/europeana/EDM.md`** — Narrative overview of EDM entity relationships, RDF namespaces, and rights framework. Complements `edm.yaml` with context on how classes relate to each other and the overall data flow.

### Other documentation

Always read from these local copies rather than fetching from the web:

- **`docs/qlever/docs/`** — Full QLever documentation (upstream MkDocs source). Covers Qleverfile format, SPARQL compliance, text/geo/path search, materialized views, benchmarks, troubleshooting, and more. Read these when working on index configuration, Qleverfile generation, query features, or debugging QLever behavior.
- **`docs/europeana/Europeana Knowledge Base/`** — Europeana's knowledge base (exported from Confluence space `EF`). Includes EDM mapping guidelines (per-class property documentation for ProvidedCHO, Aggregation, WebResource, contextual classes), publishing guides (content/metadata tiers, rights statements), semantic enrichments, API docs, terminology, and media policy. Read these for detailed EDM field semantics, data quality rules, or Europeana-specific conventions beyond what `EDM.md` covers. Images embed live Confluence URLs (no local attachment files).

### Updating documentation

Doc sets and references are updated via standalone uv scripts:

```bash
uv run scripts/update-all.py                   # Run every update-*.py in dependency order
uv run scripts/update-edm-schema.py            # Regenerate schema/edm.yaml from ontology sources
uv run scripts/update-metis-vocabularies.py    # Sync Europeana's Metis vocabulary registry
uv run scripts/update-qlever-docs.py           # Sync QLever docs from GitHub (full replace)
uv run scripts/update-europeana-docs.py        # Sync Europeana KB from Confluence (incremental)
```

The orchestrator (`update-all.py`) accepts `--only NAME [...]` and `--skip NAME [...]` to scope a run; e.g. `uv run scripts/update-all.py --only metis-vocabularies`.

The `update-edm-schema.py` script clones europeana/metis-schema to `/tmp`, copies XSD+OWL files to `references/ontologies/metis-schema/`, fetches external ontology RDF files (DC, DCTERMS, SKOS, FOAF, ORE, etc.) to `references/ontologies/external/`, and generates `edm.yaml` with descriptions from all sources. Description priority: EDM OWL > XSD annotations > external ontologies > hardcoded fallbacks. Use `--no-external-descriptions` to skip incorporating external descriptions.

The `update-metis-vocabularies.py` script clones europeana/metis-vocabularies to `/tmp` and copies the `src/main/resources/` tree (47 YAML metadata files + 46 XSL mapping files) to `references/vocabularies/metis-vocabularies/`. This registry is Europeana's own canonical list of authority URI patterns used by Metis enrichment — the `schema_loader.metis_vocabularies()` helper loads the YAMLs at runtime and is the source of truth for `x_authority` classification on `map_sameAs`.

The Europeana script uses `confluence-markdown-exporter` with anonymous access. A lockfile (`docs/europeana/confluence-lock.json`) tracks Confluence page version numbers so subsequent runs only re-export pages that changed. After export, local attachment references are rewritten to remote Confluence download URLs and the attachment files are deleted (so binary files are never committed).

## Europeana EDM domain context

For the complete EDM class and property reference, see `schema/edm.yaml`. For narrative context on entity relationships, RDF namespaces, and rights framework, see `docs/europeana/EDM.md`. For detailed per-class property documentation and mapping guidelines, see `docs/europeana/Europeana Knowledge Base/EDM - Mapping guidelines/`. For QLever engine internals and configuration, see `docs/qlever/docs/`.

The data follows the **Europeana Data Model (EDM)**. Key entities:

- **ProvidedCHO** — the cultural heritage object
- **ore:Proxy** — descriptive metadata (there's a provider proxy and a Europeana proxy per item)
- **ore:Aggregation** — links to digital representations (WebResources)
- **edm:Agent**, **edm:Place**, **skos:Concept**, **edm:TimeSpan** — contextual entities

The provider proxy (identified by `FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" }`) holds the primary descriptive metadata (dc:title, dc:creator, etc.). The Europeana proxy (`edm:europeanaProxy "true"`) holds normalised enrichments (edm:year).

### Query, Export, and Filter types

**`Query`** (`query.py`) represents a named SPARQL query with a `sparql(filters)` method that generates query text on demand. `QueryRegistry` builds the SPARQL queries at construction time — one `values_<Class>` query per EDM class plus one `links_<Class>__<property>` query per link property. `SparqlHelpers` provides reusable EDM triple pattern fragments.

**`QueryFilters`** carries optional filter parameters (countries, types, reuse_level, year_from/to, institutions, aggregators, min_completeness, filter_languages, dataset_names, limit, sample_size, etc.) and expresses itself as SPARQL via `to_sparql()` and `limit_clause()`. Rights URIs are classified into "open", "restricted", and "prohibited" reuse levels by the registry in `rights.py`.

**`Export`** (`export.py`) is the base class for anything producing a Parquet file (or Hive-partitioned directory). `QueryExport` wraps a `Query` with a frozen SPARQL string; link partition scans carry `partition_of` (parent table) and `partition_column` (e.g. `v_dc_subject`) so they write to `<parent>/x_property=<col>/data.parquet`. `CompositeExport` holds `ComposeStep` objects and a `depends_on` list — for `links_*` tables the compose list is empty and the export acts purely as a dependency aggregator. `ExportRegistry` builds all 38 final exports plus the synthetic per-property link partition scans. `ExportPipeline` executes exports in dependency order.

**`ExportSet`** (`export.py`) is a named, non-exclusive collection of export names, driven by `export_sets` annotations in `edm_parquet.yaml`. Built-in sets: `pipeline` (38 — all final exports), `raw` (26 — values_* + links_*), `group` (1 — `group_items`), `maps` (5 — `map_rights`, `map_sameAs`, `map_cho_entities`, `map_edm_entities`, `map_cho_mimetypes`), `explorer` (everything the browser explorer needs: `group_items`, contextual `values_*` tables, `links_ore_Proxy`, the `explorer_*` derived tables, `map_cho_mimetypes`). Accessible via `--set` CLI flag; `--set all` covers the full registry.

**Naming conventions** (from `edm_parquet.yaml`):

- Tables start with one of four prefixes: `values_` (wide, one row per entity), `links_` (long, one row per value, Hive-partitioned), `group_` (pre-computed per-CHO dimensions, wide scalar), `map_` (static lookup / navigation).
- Columns start with one of three prefixes: `k_` (identifier / foreign key), `v_` (scalar EDM property straight from the RDF), `x_` (extracted / computed / resolved / aggregated).
- Column names derive mechanically from EDM CURIEs: `dc:subject` → `v_dc_subject`, `ebucore:fileByteSize` → `v_ebucore_fileByteSize`, `skos:prefLabel` → `v_skos_prefLabel`.

**Raw layer** (`values_*` + `links_*`): There is one `values_<Class>` and one `links_<Class>` table per EDM class with descriptive properties — 15 values tables (for all 12 EDM classes plus `edm:PersistentIdentifier`, `edm:PersistentIdentifierScheme`, and `values_publishing_tier` for content/metadata-tier annotations) and 11 links tables. Each `links_<Class>` is a Hive-partitioned directory with one sub-directory per link property (e.g. `links_ore_Proxy/x_property=v_dc_subject/data.parquet`). Individual partition scans can be exported by name (e.g. `links_ore_Proxy__dc_subject`) or via `--property dc_subject` on the parent table. Per-CHO descriptive metadata (titles, subjects, creators, dates, etc.) lives here — join `links_ore_Proxy` through `values_ore_Proxy.k_iri_cho` to reach the CHO.

**Composite layer** (`group_items`, `map_*`, `explorer_*`):

- `group_items` is a wide, scalar-only per-CHO table designed for fast analytics (grouping, filtering, counting) — all categorical/boolean/integer columns, no lists. Contains the computed `x_reuse_level`, `x_rights_family`, the publishing `x_content_tier` / `x_metadata_tier` columns, and `x_has_*` boolean flags. A previous `merged_items` table that flattened multi-valued properties into LIST\<STRUCT\> columns was removed — the join tree did not fit in memory on the 60 M-CHO dataset, and downstream queries against the raw `links_ore_Proxy` Hive directory are both simpler and cheaper.
- `map_rights` maps every distinct `edm:rights` URI to rights family and reuse level. `map_sameAs` collects cross-entity sameAs links and tags each one with `x_well_formed` (basic IRI hygiene), `x_metis_known` (matches a vocabulary in the Metis registry, see `references/vocabularies/metis-vocabularies/`), and `x_authority` (Metis vocabulary short name when both bools are true; NULL otherwise). `map_cho_entities` resolves the CHO→entity reference graph; `map_edm_entities` summarises the EDM contextual entities themselves; `map_cho_mimetypes` resolves CHO → MIME-type lookups for media-type analytics and explorer facets.
- `explorer_*` tables (`explorer_edm_entities`, `explorer_concepts`, `explorer_agents`, `explorer_places`, `explorer_timespans`, `explorer_facet_top_n`) are precomputed for the browser explorer — slim entity tables for IRI-label resolution and a top-N facet cache for fast initial rendering.

## Conventions

- All data-processing logic is in the Python CLI. No bash scripts for pipeline steps.
- CLI commands are in `cli.py`, business logic in `merge.py`/`export.py`/`query.py`/`compose.py`/`rights.py`/`validate.py`/`throttle.py`, schema access in `schema_loader.py`, configuration in `constants.py`, resource detection in `resources.py`, live display in `dashboard.py`/`display.py`, state tracking in `state.py`, telemetry in `telemetry.py`, composable reporting in `report.py`, NL querying in `ask/`, browser-based exploration in `explorer/`.
- **Two-layer LinkML schema**: `schema/edm.yaml` is the primary source of truth for the EDM data model — 12 classes, 242 fully-described attributes generated from the metis-schema XSD+OWL, XSD documentation annotations, and external vocabulary ontologies (DC, DCTERMS, SKOS, FOAF, etc.) cached in `references/ontologies/`. `schema/edm_parquet.yaml` imports `edm.yaml` and declares all 38 export tables (15 `values_*` + 11 `links_*` + `group_items` + 5 `map_*` + 6 `explorer_*`) as LinkML classes — each with `export_type`, `export_sets`, `sparql_base_pattern`, and per-column annotations. Runtime code reads the export schema via `schema_loader.py`. The base EDM schema serves as a "menu" for designing new exports; regenerate it with `uv run scripts/update-edm-schema.py`.
- **Fully declarative exports**: Every final export (`values_*`, `links_*`, `group_items`, `map_*`, `explorer_*`) is a LinkML class in `edm_parquet.yaml` with annotations that drive SPARQL generation, DuckDB composition, PyArrow schemas, and export set membership. Adding a new export requires only editing the YAML — no Python code changes. `schema_loader.export_classes()` discovers all exports; `schema_loader.links_scan_entries()` enumerates the synthetic per-property partition scans; `schema_loader.pyarrow_schema(name)` returns static PyArrow schemas; `query.py` generates SPARQL from `sparql_base_pattern` annotations; `export.py` builds export sets from `export_sets` annotations.
- **No unit tests.** This project does not use unit tests. Do not create test files or run pytest.
- Use `rich.console.Console` for all terminal output (not bare `print`).
- Click options use `Path` type with `path_type=Path`.
