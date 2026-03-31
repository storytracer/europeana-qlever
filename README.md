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

A background **resource monitor** runs throughout the pipeline, sampling RSS, available memory, disk space, and CPU usage every 1-2 seconds. Samples are logged to `<work-dir>/monitor.log` (CSV). Console warnings appear when system memory exceeds 80% (warning) or 90% (critical). During merge, an **adaptive throttle** dynamically adjusts worker concurrency based on CPU and memory pressure, using hysteresis to avoid jitter.

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
```

The `start` command regenerates the Qleverfile with current resource budgets before launching. Verify with a basic query:

```bash
curl -Gs http://localhost:7001 \
  --data-urlencode 'query=SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }' \
  --data-urlencode 'action=tsv_export'
```

#### 6. Export to Parquet

Export runs SPARQL queries against the server and writes Parquet files to `<work-dir>/exports/`:

```bash
# Export all base queries (6 queries)
uv run europeana-qlever -d /data/europeana export --all

# Export a specific named query
uv run europeana-qlever -d /data/europeana export -q items_enriched

# Export all 18 user-facing queries
uv run europeana-qlever -d /data/europeana export --query-set all

# Custom .sparql file
uv run europeana-qlever -d /data/europeana export path/to/custom_query.sparql
```

#### 7. Stop the server

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
├── start                      Start the QLever SPARQL server
├── stop                       Stop the QLever SPARQL server
├── list-queries               List all available named queries by category
├── analyze
│   ├── qlever                 Profile queries against a running QLever server
│   └── static                 Offline structural analysis via SPARQL algebra
├── export                     Export SPARQL query results as Parquet files
└── pipeline TTL_DIR           Run the full pipeline: merge → index → start → export → stop
```

## Query system

SPARQL queries are generated dynamically by the `QueryBuilder` class. Queries are organized into four categories:

| Category | Count | Description |
|----------|-------|-------------|
| **Example** | 11 | Analytical distributions: items by type, country, language, year, provider; MIME types, IIIF availability, etc. |
| **Base** | 6 | Entity-level exports: web resources, rights/providers, agents, places, concepts, timespans |
| **Component** | 8 | Flat SPARQL scans (no GROUP BY) that serve as building blocks for composite exports: items_core, items_titles, items_descriptions, items_subjects, items_dates, items_languages, items_years, items_creators |
| **Enriched** | 1 | `items_enriched` -- denormalized composite export built from component tables via DuckDB |

There are 18 user-facing queries (example + base + enriched). Component queries are also individually addressable via `-q items_core`, etc., but are primarily building blocks that `items_enriched` depends on and exports automatically.

List all queries:

```bash
uv run europeana-qlever -d /data/europeana list-queries
```

### Hybrid export architecture

Composite queries like `items_enriched` use a two-phase export:

- **Phase 1 (QLever):** Simple, flat SPARQL scans export to Parquet "base tables" -- no GROUP BY, no GROUP_CONCAT, minimal OPTIONALs. QLever does what it's best at: index scans and triple pattern matching over billions of triples.
- **Phase 2 (DuckDB):** SQL joins the base table Parquet files, resolves language priorities, aggregates multi-valued properties (using native `LIST` and `STRUCT` Parquet types), and produces the final denormalized export.

Dependencies are resolved automatically -- exporting `items_enriched` transparently exports all 8 component tables first.

### Export examples

```bash
# All 6 base queries
uv run europeana-qlever -d /data/europeana export --all

# A specific named query (composite dependencies auto-exported)
uv run europeana-qlever -d /data/europeana export -q items_enriched

# All example queries
uv run europeana-qlever -d /data/europeana export --query-set examples

# Every query (examples + base + enriched = 18)
uv run europeana-qlever -d /data/europeana export --query-set all

# Filtered export: openly-licensed images from the Netherlands
uv run europeana-qlever -d /data/europeana export -q items_enriched \
  --country Netherlands --type IMAGE --rights-category open

# Sample 10,000 items for development
uv run europeana-qlever -d /data/europeana export -q items_enriched --limit 10000

# Custom .sparql files
uv run europeana-qlever -d /data/europeana export path/to/custom_query.sparql
```

### Filter options

All filter options apply to named queries (`-q`, `--query-set`, `--all`):

| Option | Description |
|--------|-------------|
| `--country` | Filter by country (repeatable) |
| `--type` | Filter by edm:type: TEXT, IMAGE, SOUND, VIDEO, 3D (repeatable) |
| `--rights-category` | Filter by rights: open, restricted, permission |
| `--provider` | Filter by dataProvider (repeatable) |
| `--min-completeness` | Minimum completeness score (1-10) |
| `--year-from` / `--year-to` | edm:year range |
| `--language` | Additional language(s) for label resolution, beyond English and the item's own language. Produces extra columns. Repeatable |
| `--dataset-name` | Filter by datasetName (repeatable) |
| `--limit` | LIMIT clause for all queries |

### Export control options

| Option | Default | Description |
|--------|---------|-------------|
| `--skip-existing` | off | Skip queries whose `.parquet` already exists |
| `--keep-base / --no-keep-base` | keep | Retain or delete intermediate component table Parquets after composition |
| `--reuse-tsv` | off | Skip SPARQL download if the `.tsv` file already exists (useful for re-testing Parquet conversion) |
| `--duckdb-memory` | auto (75% RAM) | DuckDB memory budget for Phase 2 composition (e.g. `4GB` or `auto`) |
| `--timeout` | 3600 | Per-query timeout in seconds |

### Language resolution

Queries resolve multilingual labels using a parallel English + vernacular model:

- **`items_enriched`** produces parallel columns: `title_en` (English), `title_native` (item's own language from `dc:language`), `title_native_lang` (ISO 639 code), and `title` (resolved best-available) -- composed via DuckDB from component tables.
- **Entity labels** (creator names, subject terms) resolve via English -> any available.

Add more languages with `--language`:

```bash
uv run europeana-qlever -d /data/europeana export -q items_enriched --language fr --language de
```

This adds `title_fr`, `title_de`, `description_fr`, `description_de` columns.

### Query analysis

The `analyze` command has two modes for diagnosing query performance:

```bash
# Runtime profiling against a running QLever server (collects execution tree metadata)
uv run europeana-qlever -d /data/europeana analyze qlever -q items_core --limit 1000

# Offline structural analysis (no server needed, uses SPARQL algebra)
uv run europeana-qlever -d /data/europeana analyze static -q items_core

# Analyze all enriched queries
uv run europeana-qlever -d /data/europeana analyze static --query-set enriched
```

Both modes produce Markdown reports in `<work-dir>/analysis/`. The `qlever` mode identifies runtime bottlenecks from the execution tree; the `static` mode identifies structural complexity (OPTIONAL nesting depth, triple pattern count, aggregate cost).

## Directory layout

**Repository:**

| Directory / File | Purpose |
|-----------|---------|
| `src/europeana_qlever/` | Python CLI source code (14 modules, ~6,900 lines) |
| `tests/` | Unit tests (query, export, compose, validate, throttle, state, analysis) |
| `EDM.md` | Europeana Data Model reference -- entity relationships, RDF namespaces, rights framework |
| `docs/qlever/docs/` | QLever documentation (upstream MkDocs source) -- Qleverfile format, SPARQL compliance, text/geo/path search, troubleshooting |
| `docs/europeana/` | Europeana Knowledge Base -- EDM mapping guidelines, publishing guides, semantic enrichments, API docs |

**Work directory** (specified via `-d`):

| Path | Purpose |
|------|---------|
| `ttl-merged/` | Merged chunk TTL files (~5 GB each) |
| `index/` | Qleverfile, settings.json, Qleverfile-ui.yml, and QLever index files |
| `exports/` | Parquet output files (TSV intermediates are deleted) |
| `analysis/` | Query performance analysis Markdown reports |
| `monitor.log` | Resource monitor log (CSV: timestamp, RSS, available memory, disk free, CPU) |
| `pipeline_state.json` | Pipeline checkpoint for resume-on-failure |

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
