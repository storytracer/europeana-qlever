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

#### 1. Download the Europeana TTL dump

The full dump lives at `ftp://download.europeana.eu/dataset/TTL/` (anonymous FTP, ~15,000+ ZIP files). Configure rclone with the Europeana remote, then:

```bash
rclone -P copy europeana:dataset/TTL/ ~/data/europeana/metadata/TTL/ --transfers=10 --checkers=8
```

#### 2. Merge TTL files

Merging discovers all RDF prefixes (via rdflib sampling) and extracts ZIPs in parallel into chunked TTL files (~5 GB each) with a unified prefix header.

```bash
uv run europeana-qlever merge
```

Options:

```bash
uv run europeana-qlever merge \
  --ttl-dir ~/data/europeana/metadata/TTL \
  --merged-dir ~/data/europeana/metadata/TTL-merged \
  --chunk-size 5.0 \
  --workers 12 \
  --sample-size 100
```

You can also run prefix discovery standalone:

```bash
uv run europeana-qlever scan-prefixes --sample-size 100 --files-per-zip 5
```

#### 3. Generate the Qleverfile

```bash
uv run europeana-qlever write-qleverfile --qlever-bin /path/to/qlever/build
```

This writes a `Qleverfile` and `settings.json` into `europeana-index/` with EDM-optimised settings (all languages kept, external prefixes for long URIs, Unicode support, etc.).

#### 4. Build the index

```bash
uv run europeana-qlever index
```

This takes approximately 2–5 hours depending on hardware. Run in tmux or screen for long sessions.

#### 5. Start the SPARQL server

```bash
uv run europeana-qlever start
```

Verify with a basic query:

```bash
curl -Gs http://localhost:7001 \
  --data-urlencode 'query=SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }' \
  --data-urlencode 'action=tsv_export'
```

#### 6. Export to Parquet

```bash
# List available queries
uv run europeana-qlever export --list-queries

# Export specific queries
uv run europeana-qlever export --query core_metadata --query agents

# Export everything
uv run europeana-qlever export

# Skip already-exported queries
uv run europeana-qlever export --skip-existing --timeout 7200
```

## CLI commands

```
europeana-qlever
├── scan-prefixes     Discover all RDF prefixes used across the TTL dump
├── merge             Merge all Europeana TTL ZIPs into chunked TTL files
├── write-qleverfile  Generate a Qleverfile configured for the Europeana dataset
├── index             Build the QLever index from merged TTL chunks
├── start             Start the QLever SPARQL server
└── export            Export SPARQL query results as Parquet files
```

## Pre-defined export queries

| Name | Description |
|------|-------------|
| `core_metadata` | Title, creator, date, type, subject, language, rights, country, data provider |
| `web_resources` | Digital representation URLs with MIME type, dimensions, file size |
| `agents` | People/orgs with multilingual labels, dates, profession, Wikidata links |
| `places` | Locations with coordinates, labels, Wikidata links |
| `concepts` | SKOS concepts with hierarchy, scheme, cross-scheme matches |
| `rights_and_providers` | Item-level rights statements with provider, country, completeness score |

### Adding custom queries

Add entries to `EXPORT_QUERIES` in `src/europeana_qlever/constants.py`:

```python
EXPORT_QUERIES["my_custom_export"] = """\
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX ore: <http://www.openarchives.org/ore/terms/>
SELECT ?item ?title WHERE {
  ?proxy ore:proxyFor ?item ;
         dc:title ?title .
  FILTER(CONTAINS(LCASE(?title), "vermeer"))
}"""
```

Then export: `uv run europeana-qlever export --query my_custom_export`

## Directory layout

| Directory | Purpose |
|-----------|---------|
| `src/europeana_qlever/` | Python CLI source code |
| `europeana-index/` | Qleverfile, settings.json, and index files (generated) |
| `~/data/europeana/metadata/TTL/` | Downloaded ZIP files from Europeana FTP |
| `~/data/europeana/metadata/TTL-merged/` | Merged chunk TTL files |
| `~/europeana-exports/` | TSV + Parquet output files |

## Refreshing the data

Europeana refreshes the FTP dump weekly. To update:

1. Re-download changed ZIPs: `rclone -P copy europeana:dataset/TTL/ ~/data/europeana/metadata/TTL/ --transfers=10`
2. Re-merge: `uv run europeana-qlever merge`
3. Re-index: `uv run europeana-qlever index` (QLever does not support incremental updates; full re-index is needed)
4. Restart: `uv run europeana-qlever start`

## License

[Apache 2.0](LICENSE)
