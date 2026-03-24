# europeana-qlever

CLI for ingesting the full Europeana EDM metadata dump (~66 million records, 2–5 billion triples in Turtle format) into a [QLever](https://github.com/ad-freiburg/qlever) SPARQL engine and exporting query results as Parquet files.

## Overview

The pipeline downloads Europeana's bulk TTL dump, merges thousands of small ZIP archives into chunked TTL files with unified prefixes, builds a QLever index, serves a SPARQL endpoint, and exports structured query results to Parquet via DuckDB.

```
Europeana FTP (15,000+ ZIPs)
  → merge (parallel extraction, prefix unification)
  → QLever index (~2–5 hours)
  → SPARQL endpoint (localhost:7001)
  → Parquet export (DuckDB + zstd compression)
```

## Dataset sizing

| Metric | Estimate |
|--------|----------|
| Records | ~66 million |
| Triples per record | ~30–80 |
| Total triples | ~2–5 billion |
| Compressed TTL on FTP | ~50–120 GB |
| Uncompressed TTL | ~200–500 GB |
| QLever index size | ~100–250 GB |
| RAM for indexing | ~20–30 GB |
| RAM for query serving | ~10–20 GB |

Total disk footprint is approximately 600–800 GB (ZIPs + merged TTL + index + working space).

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — Python project manager
- **[QLever](https://github.com/ad-freiburg/qlever)** — either compiled from source or installed via package. The `qlever` CLI tool should also be installed (`uv tool install qlever`).
- **[rclone](https://rclone.org/)** — for downloading the Europeana FTP dump
- **Docker** (optional) — only needed for the QLever UI

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

## Usage

Every command requires a **work directory** (`-w` / `--work-dir`), where all output is written. You can also set the `EUROPEANA_QLEVER_WORK_DIR` environment variable instead of passing `-w` each time.

The work directory contains these subdirectories (created automatically as needed):

```
<work-dir>/
├── ttl-merged/    # Merged chunk TTL files
├── index/         # Qleverfile, settings.json, QLever index files
└── exports/       # Parquet output files
```

#### 1. Download the Europeana TTL dump

The full dump lives at `ftp://download.europeana.eu/dataset/TTL/` (anonymous FTP, ~15,000+ ZIP files). Configure rclone with the Europeana remote, then download to a directory of your choice:

```bash
rclone -P copy europeana:dataset/TTL/ ~/data/europeana/TTL/ --transfers=10 --checkers=8
```

#### 2. Merge TTL files

Merging discovers all RDF prefixes (via rdflib sampling) and extracts ZIPs in parallel into chunked TTL files (~5 GB each) with a unified prefix header. Pass the source TTL directory as an argument:

```bash
uv run europeana-qlever -w /data/europeana merge ~/data/europeana/TTL
```

Options:

```bash
uv run europeana-qlever -w /data/europeana merge ~/data/europeana/TTL \
  --chunk-size 5.0 \
  --workers 12 \
  --sample-size 100
```

You can also run prefix discovery standalone:

```bash
uv run europeana-qlever -w /data/europeana scan-prefixes ~/data/europeana/TTL \
  --sample-size 100 --files-per-zip 5
```

#### 3. Generate the Qleverfile

```bash
uv run europeana-qlever -w /data/europeana write-qleverfile --qlever-bin /path/to/qlever/build
```

This writes a `Qleverfile` and `settings.json` into `<work-dir>/index/` with EDM-optimised settings (all languages kept, external prefixes for long URIs, Unicode support, etc.).

#### 4. Build the index

```bash
uv run europeana-qlever -w /data/europeana index
```

This takes approximately 2–5 hours depending on hardware. Run in tmux or screen for long sessions.

#### 5. Start the SPARQL server

```bash
uv run europeana-qlever -w /data/europeana start
```

Verify with a basic query:

```bash
curl -Gs http://localhost:7001 \
  --data-urlencode 'query=SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }' \
  --data-urlencode 'action=tsv_export'
```

#### 6. Export to Parquet

Export runs SPARQL queries against the server and writes Parquet files to `<work-dir>/exports/` (intermediate TSV files are deleted automatically):

```bash
# Export all bundled queries
uv run europeana-qlever -w /data/europeana export --all

# Export specific query files
uv run europeana-qlever -w /data/europeana export path/to/custom_query.sparql

# Skip already-exported queries
uv run europeana-qlever -w /data/europeana export --all --skip-existing --timeout 7200
```

#### 7. Stop the server

```bash
uv run europeana-qlever -w /data/europeana stop
```

#### Full pipeline

Run everything end-to-end (merge → write-qleverfile → index → start → export → stop):

```bash
uv run europeana-qlever -w /data/europeana pipeline ~/data/europeana/TTL

# Skip stages whose output already exists
uv run europeana-qlever -w /data/europeana pipeline ~/data/europeana/TTL --skip-merge --skip-index
```

## CLI commands

All commands require `-w <work-dir>` (or `EUROPEANA_QLEVER_WORK_DIR` env var).

```
europeana-qlever -w WORK_DIR
├── scan-prefixes TTL_DIR      Discover all RDF prefixes used across the TTL dump
├── merge TTL_DIR              Merge all Europeana TTL ZIPs into chunked TTL files
├── write-qleverfile           Generate a Qleverfile configured for the Europeana dataset
├── index                      Build the QLever index from merged TTL chunks
├── start                      Start the QLever SPARQL server
├── stop                       Stop the QLever SPARQL server
├── export [FILES...] | --all  Export SPARQL query results as Parquet files
└── pipeline TTL_DIR           Run the full pipeline: merge → index → start → export → stop
```

## Pre-defined export queries

SPARQL queries are bundled inside the package at `src/europeana_qlever/queries/`. They are numbered for execution order:

| File | Description |
|------|-------------|
| `01_core_metadata.sparql` | Title, creator, date, type, subject, language, rights, country, data provider |
| `02_web_resources.sparql` | Digital representation URLs with MIME type, dimensions, file size |
| `03_rights_and_providers.sparql` | Item-level rights statements with provider, country, completeness score |
| `04_agents.sparql` | People/orgs with multilingual labels, dates, profession, Wikidata links |
| `05_places.sparql` | Locations with coordinates, labels, Wikidata links |
| `06_concepts.sparql` | SKOS concepts with hierarchy, scheme, cross-scheme matches |

Run all bundled queries with `--all`:

```bash
uv run europeana-qlever -w /data/europeana export --all
```

### Adding custom queries

You can also pass custom `.sparql` files directly:

```sparql
# vermeer_titles.sparql
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
SELECT ?item ?title WHERE {
  ?proxy ore:proxyFor ?item ;
         dc:title ?title .
  FILTER(CONTAINS(LCASE(?title), "vermeer"))
}
```

Then export: `uv run europeana-qlever -w /data/europeana export vermeer_titles.sparql`

## Directory layout

**Repository:**

| Directory | Purpose |
|-----------|---------|
| `src/europeana_qlever/` | Python CLI source code |
| `src/europeana_qlever/queries/` | Bundled SPARQL export queries (`.sparql` files) |

**Work directory** (specified via `-w`):

| Subdirectory | Purpose |
|--------------|---------|
| `ttl-merged/` | Merged chunk TTL files |
| `index/` | Qleverfile, settings.json, and QLever index files |
| `exports/` | Parquet output files |

## Refreshing the data

Europeana refreshes the FTP dump weekly. To update:

1. Re-download changed ZIPs: `rclone -P copy europeana:dataset/TTL/ ~/data/europeana/TTL/ --transfers=10`
2. Re-run the pipeline: `uv run europeana-qlever -w /data/europeana pipeline ~/data/europeana/TTL`

Or step by step (QLever does not support incremental updates; full re-index is needed):

1. Re-merge: `uv run europeana-qlever -w /data/europeana merge ~/data/europeana/TTL`
2. Re-index: `uv run europeana-qlever -w /data/europeana index`
3. Restart: `uv run europeana-qlever -w /data/europeana start`
4. Re-export: `uv run europeana-qlever -w /data/europeana export --all`

## License

[Apache 2.0](LICENSE)
