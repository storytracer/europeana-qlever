# europeana-qlever

CLI for ingesting the full Europeana EDM metadata dump (~66 million records, 2-5 billion triples in Turtle format) into a [QLever](https://github.com/ad-freiburg/qlever) SPARQL engine and exporting query results as Parquet files.

## Overview

The pipeline downloads Europeana's bulk TTL dump, merges thousands of small ZIP archives into chunked TTL files with unified prefixes, builds a QLever index, serves a SPARQL endpoint, and exports structured query results to Parquet via a hybrid SPARQL + DuckDB architecture.

```
Europeana FTP (15,000+ ZIPs)
  → merge (parallel extraction, inline validation, prefix unification)
  → QLever index (~2-5 hours)
  → SPARQL endpoint (localhost:7001)
  → Parquet export (Phase 1: SPARQL → TSV → Parquet, Phase 2: DuckDB composition)
  → report (quality/coverage analytics over exported Parquets)
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

This runs: merge -> write-qleverfile -> index -> start -> export -> stop.

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

#### 6. Export to Parquet

Export runs SPARQL queries against the server and writes Parquet files to `<work-dir>/exports/`:

```bash
# Export all pipeline exports
uv run europeana-qlever -d /data/europeana export --all

# Export the flagship resolved composite (dependencies auto-exported)
uv run europeana-qlever -d /data/europeana export items_resolved

# Export all registered exports
uv run europeana-qlever -d /data/europeana export --set all
```

#### 7. Quality/coverage report

After exporting, generate a Markdown report analysing data quality and coverage:

```bash
uv run europeana-qlever -d /data/europeana report

# Include live URL reachability probing
uv run europeana-qlever -d /data/europeana report --probe-urls

# Filtered report
uv run europeana-qlever -d /data/europeana report --type IMAGE --country Netherlands
```

The report covers volume, rights distribution, language coverage, field completeness, entity link density, content types (MIME, dimensions, IIIF), and optional URL probing. Requires `items_resolved.parquet` at minimum.

#### 8. Stop the server

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
├── list-exports               List all available exports
├── analyze
│   ├── qlever                 Profile SPARQL exports against a running QLever server
│   └── static                 Offline structural analysis via SPARQL algebra
├── export                     Export data as Parquet files
├── report                     Quality/coverage report over exported Parquet files
└── pipeline TTL_DIR           Run the full pipeline: merge → index → start → export → stop
```

## Export system

Exports are organized into named, non-exclusive **export sets**:

| Set | Count | Description |
|-----|-------|-------------|
| **pipeline** | 24 | Full Parquet export pipeline: entity exports + component tables + `items_resolved` composite |
| **summary** | 18 | Dataset statistics: items by type, country, language, year, provider, rights URI, reuse level, MIME type, etc. |
| **items** | 33 | All item-related exports (pipeline + summary) |
| **entities** | 10 | Contextual entities: agents, places, concepts, timespans (core + links pattern) |
| **rights** | 5 | Rights and licensing: items by rights URI, items by reuse level |

There are 42 SPARQL queries (`QueryExport`) and 1 DuckDB composite (`CompositeExport`). Each export can belong to multiple sets.

Entity queries follow a **core + links** pattern: `*_core` queries export single-valued properties (one row per prefLabel), while `*_links` queries export multi-valued/linked properties in long format (`?property`, `?value`, `?lang` columns). This applies to all four entity types: agents, places, concepts, and timespans.

List all exports:

```bash
uv run europeana-qlever -d /data/europeana list-exports
```

### Hybrid export architecture

The flagship export `items_resolved` uses a two-phase pipeline:

- **Phase 1 (QLever):** `QueryExport` objects run simple, flat SPARQL scans to Parquet "base tables" -- no GROUP BY, no GROUP_CONCAT, minimal OPTIONALs. QLever does what it's best at: index scans and triple pattern matching over billions of triples.
- **Phase 2 (DuckDB):** `CompositeExport` joins the base table Parquet files via 23 DuckDB SQL steps, resolving entity labels, aggregating multi-valued properties (using native `LIST` and `STRUCT` Parquet types), and producing the final denormalized export.

Multi-valued columns use native Parquet types: `LIST<STRUCT<label, uri>>` for subjects/dc_types/formats, `LIST<STRUCT<name, uri>>` for creators/contributors/publishers, `LIST<VARCHAR>` for dates/years/languages/identifiers. A computed `reuse_level` column classifies `edm:rights` URIs into open/restricted/prohibited. Web resource metadata (MIME type, dimensions, file size, IIIF detection) is aggregated per item.

Dependencies are resolved automatically -- exporting `items_resolved` transparently exports all 14 component tables + entity tables first.

### Export examples

```bash
# All pipeline exports
uv run europeana-qlever -d /data/europeana export --all

# The flagship resolved composite (dependencies auto-exported)
uv run europeana-qlever -d /data/europeana export items_resolved

# All summary exports
uv run europeana-qlever -d /data/europeana export --set summary

# Every registered export
uv run europeana-qlever -d /data/europeana export --set all

# Filtered export: openly-licensed images from the Netherlands
uv run europeana-qlever -d /data/europeana export items_resolved \
  --country Netherlands --type IMAGE --reuse-level open

# Sample 10,000 items for development
uv run europeana-qlever -d /data/europeana export items_resolved --limit 10000
```

### Filter options

All filter options apply to SPARQL-based exports:

| Option | Description |
|--------|-------------|
| `--country` | Filter by country (repeatable) |
| `--type` | Filter by edm:type: TEXT, IMAGE, SOUND, VIDEO, 3D (repeatable) |
| `--reuse-level` | Filter by reuse level: open, restricted, prohibited |
| `--provider` | Filter by dataProvider (repeatable) |
| `--min-completeness` | Minimum completeness score (1-10) |
| `--year-from` / `--year-to` | edm:year range |
| `--language` | Additional language(s) for label resolution, beyond English and the item's own language. Repeatable |
| `--dataset-name` | Filter by datasetName (repeatable) |
| `--limit` | LIMIT clause for SPARQL exports |

### Export control options

| Option | Default | Description |
|--------|---------|-------------|
| `--skip-existing` | off | Skip exports whose `.parquet` already exists |
| `--keep-base / --no-keep-base` | keep | Retain or delete intermediate component table Parquets after composition |
| `--reuse-tsv` | off | Skip SPARQL download if the `.tsv` file already exists (useful for re-testing Parquet conversion) |
| `--duckdb-memory` | auto (75% RAM) | DuckDB memory budget for Phase 2 composition (e.g. `4GB` or `auto`) |
| `--timeout` | 3600 | Per-export timeout in seconds |

### Export analysis

The `analyze` command profiles SPARQL-based exports (composite exports are skipped):

```bash
# Runtime profiling against a running QLever server (collects execution tree metadata)
uv run europeana-qlever -d /data/europeana analyze qlever items_core --limit 1000

# Offline structural analysis (no server needed, uses SPARQL algebra)
uv run europeana-qlever -d /data/europeana analyze static items_core

# Analyze all summary exports
uv run europeana-qlever -d /data/europeana analyze static --set summary
```

Both modes produce Markdown reports in `<work-dir>/analysis/`. The `qlever` mode identifies runtime bottlenecks from the execution tree; the `static` mode identifies structural complexity (OPTIONAL nesting depth, triple pattern count, aggregate cost).

## Directory layout

**Repository:**

| Directory / File | Purpose |
|-----------|---------|
| `src/europeana_qlever/` | Python CLI source code (15 modules) |
| `scripts/` | Standalone uv scripts for syncing documentation |
| `scripts/update-qlever-docs.py` | Sync QLever docs from upstream GitHub repo |
| `scripts/update-europeana-docs.py` | Sync Europeana KB from Confluence (anonymous, incremental) |
| `docs/europeana/EDM.md` | Europeana Data Model reference -- entity relationships, RDF namespaces, rights framework |
| `docs/qlever/docs/` | QLever documentation (upstream MkDocs source) -- Qleverfile format, SPARQL compliance, text/geo/path search, troubleshooting |
| `docs/europeana/Europeana Knowledge Base/` | Europeana Knowledge Base -- EDM mapping guidelines, publishing guides, semantic enrichments, API docs. Exported from Confluence with images referencing live remote URLs |

**Work directory** (specified via `-d`):

| Path | Purpose |
|------|---------|
| `ttl-merged/` | Merged chunk TTL files (~5 GB each) |
| `index/` | Qleverfile, settings.json, Qleverfile-ui.yml, and QLever index files |
| `exports/` | Parquet output files (TSV intermediates are deleted) |
| `analysis/` | Query performance analysis Markdown reports |
| `telemetry.jsonl` | Structured JSONL telemetry log (command spans, resource samples, stage events) |
| `pipeline_state.json` | Pipeline checkpoint for resume-on-failure |

## Updating documentation

Both local doc sets are updated via standalone uv scripts:

```bash
uv run scripts/update-qlever-docs.py       # Sync QLever docs from GitHub (full replace)
uv run scripts/update-europeana-docs.py     # Sync Europeana KB from Confluence (incremental)
```

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
