# europeana-qlever

CLI for ingesting the full Europeana EDM metadata dump (~66 million records, 2-5 billion triples in Turtle format) into a [QLever](https://github.com/ad-freiburg/qlever) SPARQL engine and exporting query results as Parquet files. Includes a [GRASP](https://github.com/ad-freiburg/grasp) integration for natural-language querying of the Europeana knowledge graph via an LLM-powered NL-to-SPARQL agent.

## Overview

The pipeline downloads Europeana's bulk TTL dump, merges thousands of small ZIP archives into chunked TTL files with unified prefixes, builds a QLever index, serves a SPARQL endpoint, and exports structured query results to Parquet via a hybrid SPARQL + DuckDB architecture.

```
Europeana FTP (15,000+ ZIPs)
  → merge (parallel extraction, inline validation, prefix unification)
  → QLever index (~2-5 hours)
  → SPARQL endpoint (localhost:7001)
  → create-views (QLever materialized views for fast analytics)
  → Parquet export (Phase 1: raw values_* / links_* scans → Parquet
                    Phase 2: DuckDB composition → group_items, map_*)
  → report (quality/coverage analytics over exported Parquets)
  → ask (NL querying over Parquet via DuckDB, or over SPARQL via GRASP)

GRASP (natural-language querying, CLI-managed like QLever)
  → write-grasp-config (generate server config + EDM domain notes)
  → grasp-setup (build entity/property search indices from QLever)
  → grasp-start / grasp-stop (LLM agent on localhost:6789)
  → benchmark (evaluate NL→SPARQL vs NL→DuckDB accuracy on test questions)
```

## Dataset sizing

| Metric | Estimate |
|--------|----------|
| Records | ~66 million |
| Triples per record | ~30-80 |
| Total triples | ~2-5 billion |
| Compressed TTL on FTP | ~50-120 GB |
| Uncompressed TTL | ~200-500 GB |
| QLever index size | ~100-250 GB |
| RAM for indexing | ~8-15 GB (configurable via `--stxxl-memory`) |
| RAM for query serving | ~10-15 GB (configurable via `--query-memory`) |

Total disk footprint is approximately 600-800 GB (ZIPs + merged TTL + index + working space).

### Memory management

Each pipeline stage has explicit memory controls:

| Stage | Default | How memory is bounded |
|-------|---------|----------------------|
| **Merge** | adaptive | Workers stream line-by-line to temp files; `AdaptiveThrottle` dynamically adjusts concurrency based on CPU and memory pressure (starts at `workers // 2`, scales between 2 and `workers`). Invalid TTL entries are validated inline via rdflib and skipped |
| **Index** | 8 GB stxxl | Configurable via `--stxxl-memory` |
| **Query serving** | 10 GB query / 5 GB cache | Configurable via `--query-memory` / `--cache-size` |
| **Parquet export (Phase 1)** | bounded | TSV-to-Parquet conversion uses parallel rdflib parsing with bounded submission (at most `workers * 2` batches in-flight), keeping memory constant regardless of file size |
| **Parquet export (Phase 2)** | 75% available RAM | DuckDB composition uses 75% of available RAM (min 4 GB). Spills to disk when memory limit is exceeded. Configurable via `--duckdb-memory` |

A background **resource monitor** runs throughout the pipeline, sampling RSS, available memory, disk space, and CPU usage every 1-2 seconds. Samples are logged as structured JSONL events to `<work-dir>/telemetry.jsonl`. Console warnings appear when system memory exceeds 80% (warning) or 90% (critical). During merge, an **adaptive throttle** dynamically adjusts worker concurrency based on CPU and memory pressure, using hysteresis to avoid jitter.

A **live dashboard** (Rich-based terminal UI) displays real-time system resources (CPU, memory, disk), pipeline stage progress, and a scrolling log tail during the full `pipeline` command.

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** -- Python project manager
- **[QLever](https://github.com/ad-freiburg/qlever)** -- either compiled from source or installed via package
- **qlever CLI** -- install with `uv tool install qlever` or `pip install qlever`
- **[rclone](https://rclone.org/)** -- for downloading the Europeana FTP dump

### Building QLever from source

If pre-built packages are not available for your platform (e.g. ARM64), compile from source:

```bash
sudo apt install -y \
  build-essential cmake ninja-build git \
  libboost-all-dev libicu-dev libzstd-dev \
  libjemalloc-dev pkg-config python3 python3-pip

git clone --recursive -j8 https://github.com/ad-freiburg/qlever qlever-code
cd qlever-code
mkdir build && cd build
cmake -GNinja -DCMAKE_BUILD_TYPE=Release ..
ninja -j$(nproc)
```

## Installation

```bash
git clone https://github.com/europeana/europeana-qlever.git
cd europeana-qlever
uv sync
```

Verify:

```bash
uv run europeana-qlever --help
```

## Quick start

Run the full pipeline end-to-end with a single command:

```bash
uv run europeana-qlever -d /data/europeana pipeline ~/data/europeana/TTL
```

This runs: merge -> write-qleverfile -> index -> start -> create-views -> export -> stop.

Progress is checkpointed to `pipeline_state.json` so a failed or interrupted run resumes automatically when you re-run the same command. Use `--force` to clear the checkpoint and start fresh.

```bash
# Resume after interruption (automatic)
uv run europeana-qlever -d /data/europeana pipeline ~/data/europeana/TTL

# Skip stages whose output already exists
uv run europeana-qlever -d /data/europeana pipeline ~/data/europeana/TTL --skip-merge --skip-index

# Start fresh, ignoring checkpoint
uv run europeana-qlever -d /data/europeana pipeline ~/data/europeana/TTL --force
```

## Step-by-step usage

Every command requires a **work directory** (`-d` / `--work-dir`), where all output is written. You can also set the `EUROPEANA_QLEVER_WORK_DIR` environment variable.

#### 1. Download the Europeana TTL dump

The full dump lives at `ftp://download.europeana.eu/dataset/TTL/` (anonymous FTP, ~15,000+ ZIP files). Configure rclone with the Europeana remote, then download:

```bash
rclone -P copy europeana:dataset/TTL/ ~/data/europeana/TTL/ --transfers=10 --checkers=8
```

#### 2. Merge TTL files

Merging discovers RDF prefixes (via rdflib sampling), extracts ZIPs in parallel into chunked TTL files (~5 GB each) with a unified prefix header, and validates each TTL entry inline via rdflib -- invalid entries are skipped and logged.

```bash
uv run europeana-qlever -d /data/europeana merge ~/data/europeana/TTL
```

Options:

```bash
uv run europeana-qlever -d /data/europeana merge ~/data/europeana/TTL \
  --chunk-size 5.0 \
  --workers 4 \
  --sample-size 100
```

##### MD5 checksum verification

Europeana's FTP server provides `.md5sum` companion files for each ZIP. However, these files are **unreliable** -- as of March 2026, only 159 of 2,272 md5sum files (7%) match their companion ZIPs. Two issues exist on the FTP server:

1. **Stale checksums** (2,104 files): md5sum files are periodically regenerated from freshly built ZIPs that are never published to the FTP, while the actual ZIP files retain older content.

2. **Leading-zero stripping** (126 files): md5sum files contain 31 or 30 hex characters instead of the expected 32 -- leading zeros are stripped from the hash.

MD5 verification is therefore **skipped by default**. To opt in:

```bash
europeana-qlever merge --checksum-policy=warn TTL_DIR   # log mismatches, continue
europeana-qlever merge --checksum-policy=strict TTL_DIR  # skip mismatched ZIPs
```

You can also run prefix discovery standalone:

```bash
uv run europeana-qlever -d /data/europeana scan-prefixes ~/data/europeana/TTL \
  --sample-size 100 --files-per-zip 5
```

#### Validate (optional)

Run a read-only pre-flight check that parses every TTL entry with rdflib and optionally verifies MD5 checksums. No files are written.

```bash
uv run europeana-qlever -d /data/europeana validate ~/data/europeana/TTL

# Include checksum verification
uv run europeana-qlever -d /data/europeana validate ~/data/europeana/TTL --no-checksums=false
```

Note: validation is also performed inline during merge -- invalid entries are automatically skipped.

#### 3. Generate the Qleverfile

```bash
uv run europeana-qlever -d /data/europeana write-qleverfile --qlever-bin /path/to/qlever/build
```

This writes a `Qleverfile`, `settings.json`, and `Qleverfile-ui.yml` into `<work-dir>/index/` with EDM-optimised settings (all languages kept, external prefixes for long URIs, Unicode support). Memory settings are computed dynamically from available RAM.

#### 4. Build the index

```bash
uv run europeana-qlever -d /data/europeana index
```

This takes approximately 2-5 hours depending on hardware. Run in tmux or screen for long sessions. Extra arguments are forwarded to `qlever index` (e.g. `--overwrite-existing`).

#### 5. Start the SPARQL server

```bash
uv run europeana-qlever -d /data/europeana start

# Also launch the QLever web UI
uv run europeana-qlever -d /data/europeana start --ui
```

The `start` command regenerates the Qleverfile with current resource budgets before launching. Add `--ui` to also start the QLever web interface. Verify with a basic query:

```bash
curl -Gs http://localhost:7001 \
  --data-urlencode 'query=SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }' \
  --data-urlencode 'action=tsv_export'
```

#### 6. Create materialized views (optional but recommended)

```bash
uv run europeana-qlever -d /data/europeana create-views
```

Creates the `open-items` QLever materialized view — a precomputed index of openly-licensed CHOs joined with their `edm:type`. This replaces expensive `STRSTARTS(STR(?rights), ...)` filters with instant indexed lookups via `SERVICE view:open-items { ... }` in SPARQL. Add `--sample-size 10000` to also create a `sample-items` view used by `export --sample-size` for coherent smoke tests. This step is invoked automatically by the full `pipeline` command.

#### 7. Export to Parquet

Export runs SPARQL queries against the server and writes Parquet files (and Hive-partitioned directories for `links_*` tables) to `<work-dir>/exports/`:

```bash
# Export all pipeline exports
uv run europeana-qlever -d /data/europeana export --all

# Export only the raw layer (values_* + links_*)
uv run europeana-qlever -d /data/europeana export --set raw

# Export the fast-analytics group_items table (dependencies auto-exported)
uv run europeana-qlever -d /data/europeana export group_items

# Re-run a single partition of a Hive-partitioned links table
uv run europeana-qlever -d /data/europeana export links_ore_Proxy --property dc_subject
```

#### 8. Quality/coverage report

After exporting, generate a Markdown report analysing data quality and coverage:

```bash
# Bootstrap the default question set into <work-dir>/reports/questions/
uv run europeana-qlever -d /data/europeana write-report-config

# Run all sections
uv run europeana-qlever -d /data/europeana report

# Include live URL reachability probing
uv run europeana-qlever -d /data/europeana report --probe-urls

# Filtered report using the schema-driven filter grammar
uv run europeana-qlever -d /data/europeana report -f "country=NL type=IMAGE"
```

Default sections cover volume, rights, language coverage, completeness, entities, enrichment quality, content accessibility, media quality, provider leaderboards, and cross-cutting matrices. Questions with a `query` field execute as static DuckDB SQL; questions without a query are answered by the ask agent. Requires `group_items.parquet` + the raw `values_*` / `links_*` exports.

#### 9. Stop the server

```bash
uv run europeana-qlever -d /data/europeana stop
```

## CLI commands

All commands require `-d <work-dir>` (or `EUROPEANA_QLEVER_WORK_DIR` env var).

```
europeana-qlever -d WORK_DIR
├── scan-prefixes TTL_DIR      Discover all RDF prefixes used across the TTL dump
├── validate TTL_DIR           Read-only pre-flight check (rdflib parsing + optional checksums)
├── merge TTL_DIR              Merge all Europeana TTL ZIPs into chunked TTL files
├── write-qleverfile           Generate a Qleverfile configured for the Europeana dataset
├── index                      Build the QLever index from merged TTL chunks
├── start [--ui]               Start the QLever SPARQL server (and optionally the web UI)
├── stop                       Stop the QLever SPARQL server
├── create-views               Create QLever materialized views (open-items, sample-items)
├── list-exports               List all exports (use --all-partitions for per-property link scans)
├── analyze
│   ├── qlever                 Profile SPARQL exports against a running QLever server
│   └── static                 Offline structural analysis via SPARQL algebra
├── export                     Export data as Parquet files (values_*, links_*, group_items, map_*)
├── write-report-config        Copy default report question YAML files into <work-dir>/reports/questions/
├── report                     Quality/coverage report over exported Parquet files
├── ask QUESTION               NL query: --backend parquet (DuckDB, offline) or sparql (GRASP)
├── benchmark                  Run the benchmark question set against parquet, sparql, or both
├── write-grasp-config         Generate GRASP server config in <work-dir>/grasp/
├── grasp-setup                Build GRASP search indices from QLever
├── grasp-start / grasp-stop   Manage the GRASP NL→SPARQL server
└── pipeline TTL_DIR           Run the full pipeline: merge → index → start → create-views → export → stop
```

## Export system

Exports follow a raw-then-composed architecture aligned with EDM class boundaries.

**Table naming:** `values_` (wide, one row per EDM entity — scalar k_/v_ columns), `links_` (long, one row per value, Hive-partitioned by property), `group_` (scalar-only per-CHO table for fast analytics), `map_` (lookup / navigation tables).

**Column naming:** `k_` = identifier / foreign key, `v_` = scalar EDM property straight from the RDF, `x_` = extracted / computed / resolved / aggregated. Column names derive mechanically from EDM CURIEs, e.g. `dc:subject` → `v_dc_subject`.

Exports are organized into named, non-exclusive **export sets**:

| Set | Count | Description |
|-----|-------|-------------|
| **pipeline** | 29 | All final exports: raw + group + maps (the full pipeline output) |
| **raw** | 25 | Raw `values_*` and `links_*` tables — one row per EDM entity (values) or one row per value (links, Hive-partitioned) |
| **group** | 1 | Fast-analytics `group_items` table (categorical / boolean / integer columns only) |
| **maps** | 3 | Static lookup tables: `map_rights`, `map_sameAs`, `map_cho_entities` |

There are 29 final exports: 14 `values_*` tables (one per EDM class plus two for persistent identifiers), 11 `links_*` Hive-partitioned directories, and 4 composite exports (`group_items`, `map_rights`, `map_sameAs`, `map_cho_entities`). Under the hood, the 11 `links_*` tables are made up of 129 per-property SPARQL scans, each writing to `<table>/x_property=<col>/data.parquet`.

List all exports:

```bash
# Final tables only
uv run europeana-qlever -d /data/europeana list-exports

# Also show the per-property link partition scans that make up each links_* table
uv run europeana-qlever -d /data/europeana list-exports --all-partitions
```

### Hybrid export architecture

`group_items` and the `map_*` tables are built in two phases:

- **Phase 1 (QLever):** `QueryExport` objects run simple, flat SPARQL scans (no GROUP BY, no GROUP_CONCAT, minimal OPTIONALs) — one per `values_*` table, plus one per link property per `links_*` table. QLever does what it's best at: index scans and triple pattern matching over billions of triples.
- **Phase 2 (DuckDB):** `CompositeExport` joins the raw Parquets via `ComposeStep` sequences (8 steps for `group_items`, 1–3 for the maps), producing per-CHO scalar summaries and the navigation lookup tables.

`group_items` is scalar-only: one row per CHO with categorical (v_edm_type, v_edm_country, v_edm_dataProvider, …), boolean (x_has_iiif, x_has_creator, …), and integer (v_edm_completeness) columns. A computed `x_reuse_level` column classifies `edm:rights` URIs into open/restricted/prohibited, and `x_rights_family` identifies the rights family. Multi-valued descriptive metadata (titles, subjects, creators, dates, …) is **not** denormalized into `group_items` — query `links_ore_Proxy` joined through `values_ore_Proxy.k_iri_cho` when you need those directly.

Dependencies are resolved automatically — exporting `group_items` transparently exports all required `values_*`, `links_*`, and `map_*` tables first.

### Export examples

```bash
# All pipeline exports
uv run europeana-qlever -d /data/europeana export --all

# Fast-analytics per-CHO scalar table (dependencies auto-exported)
uv run europeana-qlever -d /data/europeana export group_items

# Only the raw layer (values_* + links_*)
uv run europeana-qlever -d /data/europeana export --set raw

# Every registered export
uv run europeana-qlever -d /data/europeana export --set all

# Re-run a single link partition (e.g. after one failed scan)
uv run europeana-qlever -d /data/europeana export links_ore_Proxy --property dc_subject

# Filtered export: openly-licensed images from the Netherlands
uv run europeana-qlever -d /data/europeana export group_items \
  --country Netherlands --type IMAGE --reuse-level open

# Coherent smoke test: sample 10,000 items via the sample-items view
uv run europeana-qlever -d /data/europeana create-views --sample-size 10000
uv run europeana-qlever -d /data/europeana export --all --sample-size 10000
```

### Filter options

All filter options apply to SPARQL-based exports:

| Option | Description |
|--------|-------------|
| `--country` | Filter by country (repeatable) |
| `--type` | Filter by edm:type: TEXT, IMAGE, SOUND, VIDEO, 3D (repeatable) |
| `--reuse-level` | Filter by reuse level: open, restricted, prohibited |
| `--institution` | Filter by edm:dataProvider (repeatable) |
| `--aggregator` | Filter by edm:provider (repeatable) |
| `--min-completeness` | Minimum completeness score (1-10) |
| `--year-from` / `--year-to` | edm:year range |
| `--language` | Additional language(s) for label resolution, beyond English and the item's own language. Repeatable |
| `--dataset-name` | Filter by datasetName (repeatable) |
| `--limit` | LIMIT clause for SPARQL exports |
| `--sample-size` | Restrict every export to the same sample of N CHO items via the `sample-items` materialized view (coherent smoke test) |

### Export control options

| Option | Default | Description |
|--------|---------|-------------|
| `--skip-existing` | off | Skip exports whose `.parquet` already exists |
| `--keep-base / --no-keep-base` | keep | Retain or delete intermediate raw Parquets after composition |
| `--reuse-tsv` | off | Skip SPARQL download if the `.tsv` file already exists (useful for re-testing Parquet conversion) |
| `--duckdb-memory` | auto (75% RAM) | DuckDB memory budget for Phase 2 composition (e.g. `4GB` or `auto`) |
| `--timeout` | 3600 | Per-export timeout in seconds |
| `--property` | — | For a `links_*` table, export only a single partition (e.g. `--property dc_subject`) |

### Export analysis

The `analyze` command profiles SPARQL-based exports (composite exports are skipped):

```bash
# Runtime profiling against a running QLever server (collects execution tree metadata)
uv run europeana-qlever -d /data/europeana analyze qlever values_ore_Proxy --limit 1000

# Offline structural analysis (no server needed, uses SPARQL algebra)
uv run europeana-qlever -d /data/europeana analyze static values_ore_Proxy

# Analyze all raw exports (values_* + links_*)
uv run europeana-qlever -d /data/europeana analyze static --set raw
```

Both modes produce Markdown reports in `<work-dir>/analysis/`. The `qlever` mode identifies runtime bottlenecks from the execution tree; the `static` mode identifies structural complexity (OPTIONAL nesting depth, triple pattern count, aggregate cost).

## Natural-language querying

Two backends share the same CLI interface and benchmark harness:

- **`parquet`** (default) — `AskParquet` translates natural language to DuckDB SQL over the exported Parquet files using OpenAI function calling. Offline, no servers required.
- **`sparql`** — `AskSPARQL` translates natural language to SPARQL via [GRASP](https://github.com/ad-freiburg/grasp) (Graph Retrieval Augmented Structured Prompting) running against the QLever endpoint. Requires both the QLever and GRASP servers to be running.

### Ask a one-off question

```bash
# DuckDB-backed (default) — needs exported Parquets
uv run europeana-qlever -d /data/europeana ask "How many openly-reusable items are there?"

# Pre-filter before the agent runs
uv run europeana-qlever -d /data/europeana ask -f "type=IMAGE country=NL" \
  "What is the resolution distribution?"

# GRASP-backed (NL → SPARQL)
uv run europeana-qlever -d /data/europeana ask --backend sparql \
  "How many open images are there?"

# Verbose: show the full agent trace (tool calls, intermediate results)
uv run europeana-qlever -d /data/europeana ask -v "Top 10 subjects?"
```

The parquet backend requires `OPENAI_API_KEY` in the environment. Both backends default to `gpt-4.1-mini`; override with `--model`.

### Running GRASP

GRASP is managed by the CLI like QLever — no manual `bash setup.sh` or `cd grasp` needed. Resources are bundled in `src/europeana_qlever/grasp/`; runtime config lives in `<work-dir>/grasp/`.

```bash
# Generate server config + EDM domain notes
uv run europeana-qlever -d /data/europeana write-grasp-config

# Build entity/property search indices from QLever (requires QLever on :7001)
uv run europeana-qlever -d /data/europeana grasp-setup

# Start / stop the GRASP server (port 6789)
uv run europeana-qlever -d /data/europeana grasp-start
uv run europeana-qlever -d /data/europeana grasp-stop
```

The domain notes are rendered from the structured `EdmNote` knowledge base (`src/europeana_qlever/ask/notes.py`), so the same EDM knowledge is reused by both the parquet and sparql backends.

### Benchmarking

A curated benchmark of questions about the Europeana AI data offering — multi-page items, cultural heritage filtering, licensing, geographic coverage, content quality — lives in `src/europeana_qlever/ask/benchmark.yml`. Run it against either backend (or both) via the CLI:

```bash
# All questions against the parquet backend (default)
uv run europeana-qlever -d /data/europeana benchmark

# All questions against the GRASP/SPARQL backend
uv run europeana-qlever -d /data/europeana benchmark --backend sparql

# Compare both backends side by side
uv run europeana-qlever -d /data/europeana benchmark --backend both

# A single question
uv run europeana-qlever -d /data/europeana benchmark --question 5

# Re-run only previously failed questions (timeouts / server errors)
uv run europeana-qlever -d /data/europeana benchmark --retry-failed

# Start fresh
uv run europeana-qlever -d /data/europeana benchmark --overwrite
```

The runner streams agent traces live (model reasoning, tool calls, SQL or SPARQL execution), grades each response (PASS/EMPTY/TIMEOUT/ERROR), and produces a summary table with pass rate, token usage, and latency percentiles. Results are appended to `<work-dir>/benchmark-results.jsonl`.

### Bundled GRASP resources

Files in `src/europeana_qlever/grasp/`:

| File | Purpose |
|------|---------|
| `europeana-entity.sparql` | SPARQL for extracting entity labels during index setup |
| `europeana-property.sparql` | SPARQL for extracting property URIs during index setup |
| `entities-info.sparql` | Runtime entity detail lookup template |
| `properties-info.sparql` | Runtime property detail lookup template |
| `prefixes.json` | RDF namespace mappings for the search index |

## Directory layout

**Repository:**

| Directory / File | Purpose |
|-----------|---------|
| `src/europeana_qlever/` | Python CLI source code |
| `src/europeana_qlever/schema/edm.yaml` | EDM base schema — primary source of truth for the EDM data model (12 classes, 242 fully-described attributes) |
| `src/europeana_qlever/schema/edm_parquet.yaml` | Export schema — declares all 29 export tables (14 values_* + 11 links_* + group_items + 3 map_*) as LinkML classes with SPARQL patterns and pipeline annotations |
| `src/europeana_qlever/ask/` | NL-to-SPARQL / NL-to-DuckDB agents, shared EDM domain notes, benchmark runner and question set |
| `src/europeana_qlever/grasp/` | Bundled GRASP resource files (SPARQL templates, prefix mappings) used by `write-grasp-config` and `grasp-setup` |
| `src/europeana_qlever/report_questions/` | Bundled default report question YAML files (copied to `<work-dir>/reports/questions/` by `write-report-config`) |
| `ontologies/metis-schema/` | Europeana metis-schema XSD + OWL source files (copied from GitHub) |
| `ontologies/external/` | Cached external ontology files (DC, DCTERMS, SKOS, FOAF, ORE, ODRL, etc.) |
| `scripts/` | Standalone uv scripts for schema generation and documentation sync |
| `scripts/generate-edm-schema.py` | Generate `schema/edm.yaml` from metis-schema XSD+OWL and external ontologies |
| `scripts/update-qlever-docs.py` | Sync QLever docs from upstream GitHub repo |
| `scripts/update-europeana-docs.py` | Sync Europeana KB from Confluence (anonymous, incremental) |
| `docs/europeana/EDM.md` | Europeana Data Model reference — narrative overview of EDM entities, namespaces, rights framework |
| `docs/qlever/docs/` | QLever documentation (upstream MkDocs source) — Qleverfile format, SPARQL compliance, text/geo/path search, troubleshooting |
| `docs/europeana/Europeana Knowledge Base/` | Europeana Knowledge Base — EDM mapping guidelines, publishing guides, semantic enrichments, API docs. Exported from Confluence with images referencing live remote URLs |

**Work directory** (specified via `-d`):

| Path | Purpose |
|------|---------|
| `ttl-merged/` | Merged chunk TTL files (~5 GB each) |
| `index/` | Qleverfile, settings.json, Qleverfile-ui.yml, and QLever index files |
| `exports/` | Parquet output files — `<name>.parquet` for values_* / composites, `<name>/x_property=<col>/data.parquet` directories for Hive-partitioned links_* tables (TSV intermediates are deleted) |
| `analysis/` | Query performance analysis Markdown reports |
| `reports/` | Report output (JSON + Markdown) |
| `reports/questions/` | Report question YAML files (user-customisable; bootstrapped by `write-report-config`) |
| `grasp/` | GRASP runtime config (`europeana-grasp.yaml`, `europeana-notes.json`, search indices) |
| `telemetry.jsonl` | Structured JSONL telemetry log (command spans, resource samples, stage events) |
| `pipeline_state.json` | Pipeline checkpoint for resume-on-failure |

## Updating documentation and schemas

The EDM schema, ontology sources, and documentation are updated via standalone uv scripts:

```bash
uv run scripts/generate-edm-schema.py      # Regenerate schema/edm.yaml from ontology sources
uv run scripts/update-qlever-docs.py        # Sync QLever docs from GitHub (full replace)
uv run scripts/update-europeana-docs.py     # Sync Europeana KB from Confluence (incremental)
```

The `generate-edm-schema.py` script clones the official [europeana/metis-schema](https://github.com/europeana/metis-schema) repository, copies XSD+OWL files to `ontologies/metis-schema/`, fetches external ontology files (DC, DCTERMS, SKOS, FOAF, ORE, etc.) to `ontologies/external/`, and generates `schema/edm.yaml` with descriptions from all sources. Use `--no-external-descriptions` to skip incorporating external ontology descriptions.

The Europeana script uses `confluence-markdown-exporter` with anonymous access. A lockfile (`docs/europeana/confluence-lock.json`) tracks Confluence page version numbers so subsequent runs only re-export changed pages. Local attachment references are rewritten to remote Confluence download URLs so no binary files are committed.

## Refreshing the data

Europeana refreshes the FTP dump weekly. To update:

1. Re-download changed ZIPs: `rclone -P copy europeana:dataset/TTL/ ~/data/europeana/TTL/ --transfers=10`
2. Re-run the pipeline: `uv run europeana-qlever -d /data/europeana pipeline ~/data/europeana/TTL`

Or step by step (QLever does not support incremental updates; full re-index is needed):

1. Re-merge: `uv run europeana-qlever -d /data/europeana merge ~/data/europeana/TTL`
2. Re-index: `uv run europeana-qlever -d /data/europeana index`
3. Restart: `uv run europeana-qlever -d /data/europeana start`
4. Re-export: `uv run europeana-qlever -d /data/europeana export --all`


## License

[Apache 2.0](LICENSE)
