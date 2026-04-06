# CLAUDE.md — europeana-qlever

## What this project is

A Python CLI (`europeana-qlever`) that ingests the full Europeana EDM metadata dump (~66M records, 2–5B triples in Turtle) into a QLever SPARQL engine and exports query results as Parquet files. The pipeline: download TTL ZIPs from Europeana FTP → merge into chunked TTL → build QLever index → serve SPARQL endpoint → export to Parquet via DuckDB.

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
    edm.yaml                      # EDM base schema (generated from metis-schema XSD+OWL) — full EDM data model, 12 classes, 242 attributes
    edm_parquet.yaml              # Export schema — imports edm.yaml, declares ALL 44 export tables as LinkML classes with SPARQL patterns and pipeline annotations
  dashboard.py                    # Live Rich dashboard (system resources, pipeline progress, log tail)
  analysis.py                     # Query performance analysis: runtime (QLever) and static (SPARQL algebra)
  display.py                      # Terminal output helpers (console setup, formatting)
  compose.py                      # Schema-driven DuckDB composition SQL for hybrid SPARQL/DuckDB pipeline
  export.py                       # Export types (Export, QueryExport, CompositeExport), ExportRegistry, ExportPipeline
  merge.py                        # Parallel TTL extraction, inline validation, prefix discovery
  report.py                       # DuckDB report: ExportReport, schema-driven ReportFilters
  monitor.py                      # Background resource monitor (CPU, memory, disk, process tracking)
  query.py                        # Schema-driven SPARQL query generation (Query, QueryFilters, QueryRegistry, SparqlHelpers)
  resources.py                    # Auto-detection of system resources & budget calculation
  state.py                        # Pipeline state tracking, ValidateResult dataclass, logging setup
  telemetry.py                    # Structured JSONL telemetry (command spans, resource samples, stage events)
  throttle.py                     # Adaptive concurrency throttle (CPU/memory-aware, replaces semaphore)
  validate.py                     # Standalone validation + inline entry validation for merge
README.md                         # General-purpose project README
scripts/
  generate-edm-schema.py          # uv script: generate schema/edm.yaml from europeana/metis-schema (XSD+OWL)
  update-qlever-docs.py           # uv script: sync QLever docs from upstream GitHub repo
  update-europeana-docs.py        # uv script: sync Europeana KB from Confluence (anonymous, incremental)
docs/
  qlever/docs/                    # QLever documentation (MkDocs source from upstream)
    quickstart.md, qleverfile.md, qlever-control.md, text-search.md,
    geosparql.md, path-search.md, materialized-views.md, benchmarks.md,
    compliance.md, troubleshooting.md, faq.md, rebuild-index.md, update.md, ...
  europeana/                      # Europeana Knowledge Base (exported from Confluence)
    EDM.md                         # Europeana Data Model reference (EDM, entities, rights)
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
uv run europeana-qlever -d WORK_DIR list-exports                 # List all available exports
uv run europeana-qlever -d WORK_DIR analyze qlever items_core    # Runtime analysis against QLever
uv run europeana-qlever -d WORK_DIR analyze static items_core    # Offline structural analysis
uv run europeana-qlever -d WORK_DIR analyze static --set summary # Analyze all summary exports
uv run europeana-qlever -d WORK_DIR export --all                 # Export all pipeline exports to Parquet
uv run europeana-qlever -d WORK_DIR export --set all             # Export everything
uv run europeana-qlever -d WORK_DIR export items_resolved        # Export the flagship resolved composite
uv run europeana-qlever -d WORK_DIR pipeline TTL_DIR             # Run full pipeline end-to-end
uv run europeana-qlever -d WORK_DIR report                       # Quality/coverage report over exported Parquets
uv run europeana-qlever -d WORK_DIR report -f "country=NL,FR"    # Filtered report (any schema field)
uv run europeana-qlever -d WORK_DIR report --probe-urls          # Include live URL reachability probing
```

All commands require `-d WORK_DIR` (or `EUROPEANA_QLEVER_WORK_DIR` env var). Output paths are derived automatically. Always use `uv run` — never bare `python` or `pip install`.

## Architecture notes

- **Merge** is I/O-bound: uses `ProcessPoolExecutor` for parallel ZIP extraction. Workers stream line-by-line from ZIP entries to temp files on disk — never holding more than one line in memory — then a writer thread copies temp files into chunked output files in 1 MB reads. An `AdaptiveThrottle` (see below) dynamically bounds in-flight work based on CPU and memory pressure. Per-file `@prefix`/`@base` lines are stripped and replaced with a unified prefix header per chunk. Temp files live in `output_dir/.merge_tmp/` and are cleaned up automatically. Each ZIP entry is validated inline via rdflib parsing — invalid entries are skipped and logged. Graceful shutdown with explicit writer thread join timeouts.
- **Adaptive throttle** (`throttle.py`): `AdaptiveThrottle` replaces the old fixed `threading.Semaphore` for merge concurrency control. Starts at `max(4, workers // 2)` permits, scales between `min_permits` (2) and `max_permits` (workers) based on system CPU and memory pressure. Uses hysteresis (default 3 consecutive samples above/below thresholds) to avoid jitter. Default targets: scale down above 85% CPU or memory, scale up below 65% CPU / 70% memory. Step sizes: 2 down, 2 up. Chained into `ResourceMonitor`'s sample callback so every monitor tick triggers an adjustment check. Fires an `on_adjust` callback for live dashboard updates.
- **Validation** (`validate.py`): Provides both standalone validation (`validate` CLI command — read-only pre-flight check with rdflib parsing and optional checksum verification) and inline entry validation used during merge. `validate_entry()` parses individual TTL entries with rdflib; `validate_all()` orchestrates full validation of a TTL directory.
- **MD5 checksums** are skipped by default (`--checksum-policy=skip`) because the Europeana FTP md5sum files are unreliable. Of ~2,300 md5sum files tested (March 2026), only 7% match their companion ZIPs. The FTP server appears to regenerate md5sum files from freshly built ZIPs that are never actually published (stale checksums), and also strips leading zeros from hex hashes (126 files affected). The `validate` command's `--no-checksums` flag and the merge/pipeline `--checksum-policy` option control this behavior.
- **Prefix discovery** samples ~50 ZIPs via rdflib to catch non-standard prefixes. Falls back to regex if rdflib fails on a file. The canonical EDM prefix set is derived from the LinkML schema via `edm_schema.prefixes()`.
- **Hybrid export pipeline** uses a two-phase architecture. **Phase 1** (`QueryExport`) exports simple, flat SPARQL scans to Parquet "base tables" (no GROUP BY, no GROUP_CONCAT, minimal OPTIONALs). **Phase 2** (`CompositeExport`) uses DuckDB SQL (`compose.py`) to join the base table Parquet files, resolve language priorities, aggregate multi-valued properties, and produce final denormalized exports. This splits the workload: QLever does what it's best at (index scans, triple pattern matching over 5B triples) while DuckDB does the heavy lifting (columnar aggregation, GROUP BY, JOINs over Parquet). `CompositeExport` objects hold a list of `ComposeStep` objects executed sequentially with per-step progress logging, and transparently trigger their dependencies. The `--keep-base / --no-keep-base` flag controls whether intermediate base table Parquets are retained. TSV→Parquet conversion strips `?` prefixes from QLever column headers for clean column names.
- **Export (Phase 1)** streams multi-GB SPARQL results via httpx (chunked reads, never loaded into memory), writes TSV, then converts to Parquet via `tsv_to_parquet()` using parallel rdflib parsing (`ProcessPoolExecutor`) and PyArrow with `zstd` compression. The parallel conversion uses bounded submission (at most `workers * 2` in-flight futures) to keep memory constant regardless of file size — this is critical for large exports like `items_subjects` (258M rows, 27 GB TSV). DuckDB memory budget for Phase 2 composition is 75% of available RAM (min 4 GB, no upper cap).
- **Resource monitoring** (`monitor.py`): `ResourceMonitor` runs as a daemon thread, sampling process RSS, system available memory, disk free space, and CPU usage (system-wide and per-process including children). Samples are emitted as `resource_sample` events via the telemetry system (see below). Console warnings fire on state transitions at 80% (warn) and 90% (critical) system memory usage, also emitted as `warning` telemetry events. The monitor supports active/idle modes (1s vs 2s sampling interval) — switched to active during merge. `ResourceSnapshot` dataclass includes `cpu_pct`, `process_cpu_pct`, `process_rss_mb`, and `child_count` fields. Thresholds are configurable in `constants.py`.
- **Resource budgeting** (`resources.py`): Auto-detects system resources (CPU count, memory, disk) and computes resource budgets for merge workers, throttle targets, and writer timeouts. All parameters are overridable via CLI or constants.
- **Dashboard** (`dashboard.py`): Live Rich-based terminal dashboard showing real-time system resources (CPU, memory, disk with threshold-based coloring), pipeline stage progress, and a scrolling log tail. Auto-refreshes based on monitor samples. Redirects console output to log panel to prevent flickering.
- **Telemetry** (`telemetry.py`): Unified structured JSONL logging system. `TelemetryRecorder` appends one JSON object per line to `telemetry.jsonl` in the work directory. Events include `command_start`/`command_end` (with wall_seconds, peak_rss_mb, counters), `resource_sample` (from monitor), `stage_start`/`stage_end` (from pipeline state), and `warning` (from monitor transitions). `NullTelemetryRecorder` is a no-op for when telemetry is disabled. The `command_span` context manager wraps CLI commands to emit start/end events with timing and resource usage. Replaces the old CSV `monitor.log` approach.
- **State tracking** (`state.py`): Pipeline state persistence, `ValidateResult` dataclass for validation outcomes, and logging setup. Emits `stage_start`/`stage_end` telemetry events on state transitions via an optional `TelemetryRecorder` set with `set_telemetry()`.
- **Query generation** (`query.py`) uses `QueryRegistry` to build `Query` objects that generate SPARQL on demand via composable fragment helpers (`SparqlHelpers`). All entity queries and multi-valued item queries are generated from the LinkML schema — entity core/links queries iterate over `entity_core_fields()` and `entity_link_property_details()`, while multi-valued item queries iterate over `item_fields()` using `query_pattern` annotations (lang_tagged, iri_or_literal, simple_literal). `QueryFilters` carries filter parameters (country, type, reuse level, year range, etc.) and knows how to express itself as SPARQL (`to_sparql()`, `limit_clause()`). There are 43 SPARQL queries. Entity queries follow a **core + links** pattern: `*_core` queries export single-valued properties (one row per prefLabel), while `*_links` queries export multi-valued/linked properties in long format (`?property`, `?value`, `?lang` columns). This applies to all four entity types: agents, places, concepts, and timespans. `ExportRegistry` (`export.py`) wraps each `Query` in a `QueryExport` and adds `CompositeExport` objects. Exports are grouped into named `ExportSet`s: pipeline (24), summary (19), items (34), entities (10), rights (5).
- **Query analysis** (`analysis.py`) has two modes: `analyze qlever` sends queries to a running QLever server with `Accept: application/qlever-results+json` and `send=0` to get execution tree metadata without result transfer; `analyze static` uses rdflib's SPARQL algebra (`parseQuery` + `translateQuery`) to identify structural complexity (OPTIONAL nesting depth, triple pattern count, aggregate cost, variable fan-out) without executing queries. Both produce Markdown reports in the `analysis/` subdirectory.
- **Qleverfile generation** supports both native (compiled from source) and Docker modes. Native is preferred for performance. Memory settings are computed dynamically from available RAM by `ResourceBudget`: query memory 45%, cache 15%, cache single entry 7.5%, stxxl 25% — all relative to available memory with no hard caps (only minimum floors). Thread count is set to half of CPU count. The `write-qleverfile` command accepts `--query-memory`, `--cache-size`, and `--stxxl-memory` overrides.
- **Pipeline** (`pipeline` command) runs all stages end-to-end: merge → write-qleverfile → index → start → export → stop. Progress is checkpointed to `pipeline_state.json` so a failed or interrupted run resumes automatically; `--force` clears the checkpoint. Supports `--skip-merge` and `--skip-index` flags. The entire pipeline runs inside a `ResourceMonitor` + `Dashboard` context for continuous resource tracking and live terminal display.
- **Composition SQL** (`compose.py`) generates DuckDB SQL templates as `ComposeStep` objects (23 steps for `items_resolved` via `ComposeStep.items_resolved_steps()`), all derived from the LinkML schema. Steps are generated by iterating over `item_fields()`: multi-valued fields with `query_pattern` annotations produce aggregation steps, entity-resolved fields produce map+agg step pairs, and `reuse_level_sql()` generates the CASE/WHEN for rights classification. Column aliasing (e.g. `dataProvider→institution`) derives from schema `sparql_variable` annotations via `sparql_var()`. Templates use `{exports_dir}` as a placeholder replaced at execution time. The flagship resolved export composes 14 component tables + agents + concepts + web resources, with multi-valued property aggregation using native Parquet types (`LIST<STRUCT<label VARCHAR, uri VARCHAR>>` for subjects/dc_types/formats, `LIST<STRUCT<name VARCHAR, uri VARCHAR>>` for creators/contributors/publishers, `LIST<VARCHAR>` for dates/years/languages/identifiers/dc_rights), agent/concept label resolution via entity joins, and a computed `reuse_level` column (open/restricted/prohibited) derived from `edm:rights` URIs. Web resource metadata (MIME type, dimensions, file size, IIIF service detection) is aggregated per item. The final step is marked `is_final=True` for COPY-to-Parquet wrapping.
- **Export execution** is orchestrated by `ExportPipeline` (`export.py`). The `export --all` flag runs the pipeline export set; `--set` runs a named set; positional arguments select individual exports by name (composites like `items_resolved` transparently trigger dependencies). The `--keep-base / --no-keep-base` flag controls cleanup of intermediate component table Parquets.
- **Report** (`report.py`): `ExportReport` runs DuckDB analytics over exported Parquet files (seven sections: volume, rights, language, completeness, entities, content, optional URL probing). Returns a `Report` dataclass. `ReportFilters` is a schema-driven filter class that accepts any Item field name and generates DuckDB WHERE clauses using `filterable_fields()` from `edm_schema.py`. Filter style (``IN``, ``=``, ``list_has_any``, struct search, range) is inferred from the field's range and multivalued flag. CLI exposes a single `--filters/-f` string option parsed via `ReportFilters.parse()`.

## Documentation

Local documentation is available in three locations — always read from these local copies rather than fetching from the web:

- **`docs/europeana/EDM.md`** — Europeana Data Model reference (entity relationships, RDF namespaces, rights framework). Primary quick-reference for EDM questions.
- **`docs/qlever/docs/`** — Full QLever documentation (upstream MkDocs source). Covers Qleverfile format, SPARQL compliance, text/geo/path search, materialized views, benchmarks, troubleshooting, and more. Read these when working on index configuration, Qleverfile generation, query features, or debugging QLever behavior.
- **`docs/europeana/Europeana Knowledge Base/`** — Europeana's knowledge base (exported from Confluence space `EF`). Includes EDM mapping guidelines (per-class property documentation for ProvidedCHO, Aggregation, WebResource, contextual classes), publishing guides (content/metadata tiers, rights statements), semantic enrichments, API docs, terminology, and media policy. Read these for detailed EDM field semantics, data quality rules, or Europeana-specific conventions beyond what `EDM.md` covers. Images embed live Confluence URLs (no local attachment files).

Both doc sets are updated via standalone uv scripts:

```bash
uv run scripts/update-qlever-docs.py       # Sync QLever docs from GitHub (full replace)
uv run scripts/update-europeana-docs.py     # Sync Europeana KB from Confluence (incremental)
```

The Europeana script uses `confluence-markdown-exporter` with anonymous access. A lockfile (`docs/europeana/confluence-lock.json`) tracks Confluence page version numbers so subsequent runs only re-export pages that changed. After export, local attachment references are rewritten to remote Confluence download URLs and the attachment files are deleted (so binary files are never committed).

## Europeana EDM domain context

For comprehensive documentation on the Europeana Data Model, entity relationships, RDF namespaces, and rights framework, see `docs/europeana/EDM.md`. For detailed per-class property documentation and mapping guidelines, see `docs/europeana/Europeana Knowledge Base/EDM - Mapping guidelines/`. For QLever engine internals and configuration, see `docs/qlever/docs/`.

The data follows the **Europeana Data Model (EDM)**. Key entities:

- **ProvidedCHO** — the cultural heritage object
- **ore:Proxy** — descriptive metadata (there's a provider proxy and a Europeana proxy per item)
- **ore:Aggregation** — links to digital representations (WebResources)
- **edm:Agent**, **edm:Place**, **skos:Concept**, **edm:TimeSpan** — contextual entities

The provider proxy (identified by `FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" }`) holds the primary descriptive metadata (dc:title, dc:creator, etc.). The Europeana proxy (`edm:europeanaProxy "true"`) holds normalised enrichments (edm:year).

### Query, Export, and Filter types

**`Query`** (`query.py`) represents a named SPARQL query with a `sparql(filters)` method that generates query text on demand. `QueryRegistry` builds all 42 queries at construction time. `SparqlHelpers` provides reusable EDM triple pattern fragments.

**`QueryFilters`** carries optional filter parameters (countries, types, reuse_level, year_from/to, limit, etc.) and expresses itself as SPARQL via `to_sparql()` and `limit_clause()`. Rights URIs are classified into "open", "restricted", and "prohibited" reuse levels using pattern matching in `rights.py`.

**`Export`** (`export.py`) is the base class for anything producing a Parquet file. `QueryExport` wraps a `Query` with a frozen SPARQL string. `CompositeExport` holds `ComposeStep` objects and a `depends_on` list. `ExportRegistry` builds all exports (42 query-based + 1 composite). `ExportPipeline` executes exports in dependency order.

**`ExportSet`** (`export.py`) is a named, non-exclusive collection of export names. Built-in sets: `pipeline` (24 exports), `summary` (18), `items` (33), `entities` (10), `rights` (5). Accessible via `--set` CLI flag.

**Component exports** (`items_core`, `items_titles`, `items_descriptions`, `items_subjects`, `items_dates`, `items_languages`, `items_years`, `items_creators`, `items_contributors`, `items_publishers`, `items_dc_types`, `items_formats`, `items_identifiers`, `items_dc_rights`, `web_resources`) are flat SPARQL scans with no GROUP BY that serve as building blocks for `items_resolved`. Entity core exports (`agents_core`, `concepts_core`) are also dependencies. Available individually as positional args, e.g. `export items_core`.

**Entity core + links pattern**: Each of the four entity types (agents, places, concepts, timespans) has two queries. The `*_core` query exports single-valued properties with one row per `skos:prefLabel` (e.g. `agents_core` includes birth/death dates, gender, places). The `*_links` query exports multi-valued and linked properties in long format with `?property`, `?value`, `?lang` columns (e.g. `agents_links` includes altLabels, sameAs, broader, related, notes).

**Multi-valued columns** in `items_resolved` use native Parquet types: `LIST<STRUCT<label VARCHAR, uri VARCHAR>>` for subjects, dc_types, and formats (pairing each resolved label with its entity URI); `LIST<STRUCT<name VARCHAR, uri VARCHAR>>` for creators, contributors, and publishers (pairing each resolved display name with its entity URI, or NULL for literal-string values); `LIST<VARCHAR>` for dates, years, languages, identifiers, and dc_rights. A computed `reuse_level` column classifies `edm:rights` URIs into open/restricted/prohibited. Web resource metadata (MIME type, dimensions, file size, IIIF detection) is aggregated per item.

## Conventions

- All data-processing logic is in the Python CLI. No bash scripts for pipeline steps.
- CLI commands are in `cli.py`, business logic in `merge.py`/`export.py`/`query.py`/`compose.py`/`validate.py`/`throttle.py`, schema access in `schema_loader.py`, configuration in `constants.py`, resource detection in `resources.py`, live display in `dashboard.py`/`display.py`, state tracking in `state.py`, telemetry in `telemetry.py`, post-export analytics in `report.py`.
- **Two-layer LinkML schema**: `schema/edm.yaml` (generated from official Europeana metis-schema XSD+OWL) is the full EDM data model with all ~240 properties across 12 classes. `schema/edm_parquet.yaml` imports `edm.yaml` and declares all 44 export tables as LinkML classes — each with `export_type`, `export_sets`, `sparql_pattern`, and per-column annotations. Runtime code reads the export schema via `schema_loader.py`. The base EDM schema serves as a "menu" for designing new exports; regenerate it with `uv run scripts/generate-edm-schema.py`.
- **Fully declarative exports**: Every export (scan, summary, entity, composite, base_table) is a LinkML class in `edm_parquet.yaml` with annotations that drive SPARQL generation, DuckDB composition, PyArrow schemas, and export set membership. Adding a new export requires only editing the YAML — no Python code changes. `schema_loader.export_classes()` discovers all exports; `schema_loader.pyarrow_schema(name)` returns static PyArrow schemas; `query.py` generates SPARQL from `sparql_pattern` annotations; `export.py` builds export sets from `export_sets` annotations.
- **No unit tests.** This project does not use unit tests. Do not create test files or run pytest.
- Use `rich.console.Console` for all terminal output (not bare `print`).
- Click options use `Path` type with `path_type=Path`.
