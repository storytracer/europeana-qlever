# europeana-qlever

A Python CLI for working with the full **Europeana** cultural-heritage metadata dump as a queryable knowledge graph.

It downloads Europeana's bulk RDF dump (~66 million records, 2–5 billion triples), loads it into a [QLever](https://github.com/ad-freiburg/qlever) SPARQL engine, and exports clean, analysis-ready **Parquet** tables. On top of that, it ships:

- a quality and coverage **report** generator,
- a browser-based **explorer** for interactive faceting and charts,
- a natural-language **ask** interface (NL → SQL on Parquet, or NL → SPARQL via [GRASP](https://github.com/ad-freiburg/grasp)).

---

## Table of contents

- [What it does](#what-it-does)
- [Quick start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Step-by-step usage](#step-by-step-usage)
- [Exploring the data](#exploring-the-data)
  - [Parquet exports](#parquet-exports)
  - [Quality & coverage report](#quality--coverage-report)
  - [Browser explorer](#browser-explorer)
  - [Natural-language querying](#natural-language-querying)
- [How big is it?](#how-big-is-it)
- [CLI reference](#cli-reference)
- [Project layout](#project-layout)
- [Updating schemas & docs](#updating-schemas--docs)
- [Refreshing the data](#refreshing-the-data)
- [License](#license)

---

## What it does

The pipeline turns a folder of TTL ZIP files into a SPARQL endpoint and a set of Parquet tables you can query with DuckDB, pandas, or any standard tool.

```
Europeana FTP dump  ──►  merge  ──►  QLever index  ──►  SPARQL endpoint  ──►  Parquet exports
   (15,000+ ZIPs)                     (~2–5 hours)        (localhost:7001)      (values_*, links_*,
                                                                                 group_items, map_*)

                                            └──►  report      (quality & coverage)
                                            └──►  explore     (browser explorer)
                                            └──►  ask         (NL → SQL or NL → SPARQL)
```

All commands sit behind a single CLI: `europeana-qlever`.

---

## Quick start

After [installing](#installation):

```bash
# Download the Europeana TTL dump (one-time, large download)
rclone -P copy europeana:dataset/TTL/ ~/data/europeana/TTL/ --transfers=10

# Run the full pipeline end-to-end
uv run europeana-qlever -d /data/europeana pipeline ~/data/europeana/TTL
```

The `pipeline` command runs every stage (merge → index → start → views → export → stop) and **resumes automatically** from a checkpoint if interrupted. Use `--force` to start fresh.

Once that's done you can:

```bash
# Open the browser explorer
uv run europeana-qlever -d /data/europeana explore

# Ask a natural-language question
uv run europeana-qlever -d /data/europeana ask "How many openly-reusable images are there?"

# Generate a quality/coverage report
uv run europeana-qlever -d /data/europeana report
```

---

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — Python project manager (always use `uv run`, not bare `python` or `pip`)
- **[QLever](https://github.com/ad-freiburg/qlever)** — the SPARQL engine, either pre-built or compiled from source
- **qlever CLI** — `uv tool install qlever`
- **[rclone](https://rclone.org/)** — for downloading the Europeana FTP dump

### Building QLever from source

If pre-built packages aren't available for your platform (e.g. ARM64):

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

---

## Installation

```bash
git clone https://github.com/europeana/europeana-qlever.git
cd europeana-qlever
uv sync
uv run europeana-qlever --help
```

Every command takes a **work directory** (`-d` / `--work-dir`, or the `EUROPEANA_QLEVER_WORK_DIR` env var) where all output is written.

---

## Step-by-step usage

If you'd rather run the stages individually instead of the all-in-one `pipeline` command:

### 1. Download the TTL dump

The full dump lives at `ftp://download.europeana.eu/dataset/TTL/` (anonymous FTP, ~15,000+ ZIPs).

```bash
rclone -P copy europeana:dataset/TTL/ ~/data/europeana/TTL/ --transfers=10 --checkers=8
```

> **MD5 checksums are skipped by default.** Europeana's `.md5sum` files are unreliable: as of March 2026, only ~7 % of them actually match the companion ZIP (stale checksums and stripped leading zeros). Override with `--checksum-policy=warn` or `=strict` on `merge`/`pipeline` if you want to verify them anyway.

### 2. Merge ZIPs into TTL chunks

Extracts thousands of small ZIPs in parallel into a few large (~5 GB) TTL files with a unified prefix header. Each entry is validated inline with rdflib — invalid ones are skipped and logged.

```bash
uv run europeana-qlever -d /data/europeana merge ~/data/europeana/TTL
```

You can also run a read-only pre-flight check without writing anything:

```bash
uv run europeana-qlever -d /data/europeana validate ~/data/europeana/TTL
```

### 3. Generate the Qleverfile and build the index

```bash
uv run europeana-qlever -d /data/europeana write-qleverfile --qlever-bin /path/to/qlever/build
uv run europeana-qlever -d /data/europeana index
```

Indexing takes roughly **2–5 hours** on commodity hardware. Run it in `tmux` or `screen`. Memory settings (`--query-memory`, `--cache-size`, `--stxxl-memory`) are auto-tuned to your machine but can be overridden.

### 4. Start the SPARQL server

```bash
uv run europeana-qlever -d /data/europeana start          # SPARQL only, port 7001
uv run europeana-qlever -d /data/europeana start --ui     # also launch QLever's web UI
```

Quick sanity check:

```bash
curl -Gs http://localhost:7001 \
  --data-urlencode 'query=SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }' \
  --data-urlencode 'action=tsv_export'
```

### 5. Create materialized views (recommended)

```bash
uv run europeana-qlever -d /data/europeana create-views
```

Creates the `open-items` view (precomputed list of openly-licensed CHOs joined with their `edm:type`), so SPARQL queries can use `SERVICE view:open-items { ... }` instead of expensive `STRSTARTS` filters. Add `--sample-size 10000` to also create a `sample-items` view used for coherent smoke tests.

### 6. Export to Parquet

See [Parquet exports](#parquet-exports) below. The simplest call:

```bash
uv run europeana-qlever -d /data/europeana export --all
```

### 7. Stop the server

```bash
uv run europeana-qlever -d /data/europeana stop
```

---

## Exploring the data

### Parquet exports

The export system produces 38 final Parquet tables in `<work-dir>/exports/`. They follow a simple two-layer architecture aligned with the **Europeana Data Model (EDM)**.

#### Naming convention

| Prefix    | Kind              | Shape                                           |
| --------- | ----------------- | ----------------------------------------------- |
| `values_` | wide              | one row per EDM entity, scalar columns          |
| `links_`  | long, partitioned | one row per value, Hive-partitioned by property |
| `group_`  | wide              | per-CHO scalar table for fast analytics         |
| `map_`    | lookup            | static lookup / navigation tables               |

| Prefix | Column meaning                                       |
| ------ | ---------------------------------------------------- |
| `k_`   | identifier / foreign key                             |
| `v_`   | scalar EDM property straight from the RDF            |
| `x_`   | extracted, computed, resolved, or aggregated         |

Column names map mechanically from EDM CURIEs: `dc:subject` → `v_dc_subject`, `ebucore:fileByteSize` → `v_ebucore_fileByteSize`.

#### Export sets

Exports are grouped into named sets you can pass via `--set`:

| Set        | Count | What it contains                                                                                  |
| ---------- | ----- | ------------------------------------------------------------------------------------------------- |
| `pipeline` | 38    | All final exports (the full pipeline output)                                                      |
| `raw`      | 26    | The `values_*` and `links_*` tables straight from SPARQL                                          |
| `group`    | 1     | `group_items` — the fast per-CHO scalar table (categorical / boolean / integer)                   |
| `maps`     | 5     | `map_rights`, `map_sameAs`, `map_cho_entities`, `map_edm_entities`, `map_cho_mimetypes`           |
| `explorer` | 15    | Everything the browser explorer needs (`group_items`, contextual values, `explorer_*`, mimetypes) |

#### How exports are built

- **Phase 1 — QLever:** flat SPARQL scans (no `GROUP BY`, no `GROUP_CONCAT`, minimal `OPTIONAL`s) produce raw `values_*` and `links_*` Parquets. QLever does what it's best at: index scans over billions of triples.
- **Phase 2 — DuckDB:** joins those raw Parquets via SQL to produce the per-CHO `group_items` table, the `map_*` lookups, and the `explorer_*` derived tables.

Dependencies are resolved automatically — exporting `group_items` triggers everything it needs.

#### Common export commands

```bash
# Full pipeline output
uv run europeana-qlever -d /data/europeana export --all

# Only the raw SPARQL layer
uv run europeana-qlever -d /data/europeana export --set raw

# A single composite (dependencies auto-exported)
uv run europeana-qlever -d /data/europeana export group_items

# Re-run a single link partition
uv run europeana-qlever -d /data/europeana export links_ore_Proxy --property dc_subject

# Filtered export: open-rights images from the Netherlands
uv run europeana-qlever -d /data/europeana export group_items \
  --country Netherlands --type IMAGE --reuse-level open

# Coherent smoke test on a 10,000-CHO sample
uv run europeana-qlever -d /data/europeana create-views --sample-size 10000
uv run europeana-qlever -d /data/europeana export --all --sample-size 10000
```

List everything with `list-exports` (add `--all-partitions` to see per-property scans).

#### Filter options (apply to SPARQL exports)

| Option                       | Description                                                |
| ---------------------------- | ---------------------------------------------------------- |
| `--country`                  | Filter by country (repeatable)                             |
| `--type`                     | `TEXT`, `IMAGE`, `SOUND`, `VIDEO`, `3D` (repeatable)       |
| `--reuse-level`              | `open`, `restricted`, `prohibited`                         |
| `--institution`              | Filter by `edm:dataProvider` (repeatable)                  |
| `--aggregator`               | Filter by `edm:provider` (repeatable)                      |
| `--min-completeness`         | Minimum completeness score (1–10)                          |
| `--year-from` / `--year-to`  | `edm:year` range                                           |
| `--language`                 | Extra label languages, beyond English and the item's own   |
| `--dataset-name`             | Filter by `datasetName` (repeatable)                       |
| `--limit`                    | Apply a SPARQL `LIMIT`                                     |
| `--sample-size`              | Restrict every export to N CHOs via the `sample-items` view |

#### Profiling exports

```bash
# Runtime profile against a running server
uv run europeana-qlever -d /data/europeana analyze qlever values_ore_Proxy --limit 1000

# Offline structural analysis (uses SPARQL algebra)
uv run europeana-qlever -d /data/europeana analyze static --set raw
```

Reports go into `<work-dir>/analysis/`.

### Quality & coverage report

After exporting, generate a Markdown + JSON report covering volume, rights, providers, languages, content tiers, media, and external entity links:

```bash
# Run all bundled sections
uv run europeana-qlever -d /data/europeana report

# Run specific sections or questions
uv run europeana-qlever -d /data/europeana report -s overview
uv run europeana-qlever -d /data/europeana report -q total_items

# Filter the data
uv run europeana-qlever -d /data/europeana report -f "country=NL,FR type=IMAGE"

# Probe URL liveness
uv run europeana-qlever -d /data/europeana report --probe-urls
```

Report definitions are YAML files in `src/europeana_qlever/report_questions/`. Questions with a `query:` field run as static DuckDB SQL; questions without one are answered by the NL agent. Edit the YAMLs in place to customise.

### Browser explorer

A local browser-based explorer over `group_items.parquet` with interactive faceting, charts, and IRI-label resolution. Backed by a small threaded Python HTTP server and a shared DuckDB connection; the SPA (Preact + htm + Chart.js) is fully vendored and works offline.

```bash
# Make sure the explorer set is exported first
uv run europeana-qlever -d /data/europeana export --set explorer

# Launch (binds to port 1378, opens browser automatically)
uv run europeana-qlever -d /data/europeana explore

# Or point at a remote Parquet (e.g. on Hugging Face)
uv run europeana-qlever -d /data/europeana explore \
  --data-url https://huggingface.co/.../group_items.parquet
```

### Natural-language querying

Two backends share the same CLI and benchmark harness:

- **`parquet`** *(default)* — `AskParquet` translates NL → DuckDB SQL over the exported Parquets via OpenAI function calling. **Offline**, no servers required (just `OPENAI_API_KEY`).
- **`sparql`** — `AskSPARQL` translates NL → SPARQL via [GRASP](https://github.com/ad-freiburg/grasp) running against the QLever endpoint. Requires both QLever **and** GRASP servers running.

```bash
# DuckDB-backed (default) — needs exported Parquets
uv run europeana-qlever -d /data/europeana ask "How many openly-reusable items are there?"

# Pre-filter before the agent runs
uv run europeana-qlever -d /data/europeana ask -f "type=IMAGE country=NL" \
  "What is the resolution distribution?"

# GRASP-backed (NL → SPARQL)
uv run europeana-qlever -d /data/europeana ask --backend sparql \
  "How many open images are there?"

# Show the full agent trace
uv run europeana-qlever -d /data/europeana ask -v "Top 10 subjects?"
```

Both backends default to `gpt-4.1-mini`; override with `--model`.

#### Running GRASP

GRASP is managed by the CLI just like QLever. Resources are bundled in the package; runtime config is generated into `<work-dir>/grasp/`.

```bash
uv run europeana-qlever -d /data/europeana write-grasp-config   # generate config + EDM notes
uv run europeana-qlever -d /data/europeana grasp-setup          # build entity/property indices
uv run europeana-qlever -d /data/europeana grasp-start          # start GRASP server (port 6789)
uv run europeana-qlever -d /data/europeana grasp-stop
```

#### Benchmarks

A curated set of test questions ships in `src/europeana_qlever/ask/benchmark.yml`:

```bash
uv run europeana-qlever -d /data/europeana benchmark                    # parquet (default)
uv run europeana-qlever -d /data/europeana benchmark --backend sparql   # GRASP
uv run europeana-qlever -d /data/europeana benchmark --backend both     # compare side by side
uv run europeana-qlever -d /data/europeana benchmark --question 5
uv run europeana-qlever -d /data/europeana benchmark --retry-failed
```

The runner streams agent traces live, grades each answer (PASS/EMPTY/TIMEOUT/ERROR), and writes results to `<work-dir>/benchmark-results.jsonl`.

---

## How big is it?

| Metric                | Estimate                                |
| --------------------- | --------------------------------------- |
| Records               | ~66 million                             |
| Triples per record    | ~30–80                                  |
| Total triples         | ~2–5 billion                            |
| Compressed TTL on FTP | ~50–120 GB                              |
| Uncompressed TTL      | ~200–500 GB                             |
| QLever index size     | ~100–250 GB                             |
| RAM for indexing      | ~8–15 GB (`--stxxl-memory`)             |
| RAM for query serving | ~10–15 GB (`--query-memory`)            |

**Total disk footprint:** ~600–800 GB (ZIPs + merged TTL + index + working space).

### Memory management

Each stage has explicit memory controls:

| Stage              | Default              | How it's bounded                                                                                                   |
| ------------------ | -------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Merge              | adaptive             | Workers stream line-by-line to temp files; `AdaptiveThrottle` scales concurrency between 2 and `workers` based on CPU/memory pressure |
| Index              | 8 GB stxxl           | `--stxxl-memory`                                                                                                   |
| Query serving      | 10 GB query / 5 GB cache | `--query-memory` / `--cache-size`                                                                              |
| Export — Phase 1   | bounded              | TSV→Parquet uses parallel rdflib parsing with bounded submission (memory stays constant regardless of file size)   |
| Export — Phase 2   | 75 % of available RAM | DuckDB composition; spills to disk past the limit. `--duckdb-memory`                                              |

A background **resource monitor** samples RSS, free memory, disk, and CPU every 1–2 s and writes structured events to `<work-dir>/telemetry.jsonl`. Console warnings fire at 80 % (warn) and 90 % (critical) system memory. A live **Rich-based dashboard** shows resources, stage progress, and a log tail throughout `pipeline`.

---

## CLI reference

All commands require `-d <work-dir>` (or `EUROPEANA_QLEVER_WORK_DIR`).

```
europeana-qlever -d WORK_DIR
├── Data preparation
│   ├── scan-prefixes TTL_DIR      Discover RDF prefixes used across the dump
│   ├── validate TTL_DIR           Read-only pre-flight check (rdflib + optional checksums)
│   └── merge TTL_DIR              Merge all TTL ZIPs into chunked TTL files
│
├── QLever
│   ├── write-qleverfile           Generate a Qleverfile + settings.json
│   ├── index                      Build the QLever index from merged TTL
│   ├── start [--ui]               Start the SPARQL server (port 7001)
│   ├── stop                       Stop the server
│   └── create-views               Create materialized views (open-items, sample-items)
│
├── Exports & analysis
│   ├── list-exports               List all exports (--all-partitions for per-property scans)
│   ├── analyze qlever NAME        Runtime profile against a running server
│   ├── analyze static NAME        Offline structural analysis via SPARQL algebra
│   └── export [NAMES...]          Export Parquet tables (values_*, links_*, group_items, map_*)
│
├── Insights
│   ├── report                     Quality / coverage report over Parquet
│   ├── ask QUESTION               NL query (--backend parquet | sparql)
│   ├── benchmark                  Run the benchmark question set
│   └── explore                    Browser-based DuckDB explorer (port 1378)
│
├── GRASP (NL → SPARQL)
│   ├── write-grasp-config         Generate GRASP config + EDM domain notes
│   ├── grasp-setup                Build entity/property search indices
│   ├── grasp-start / grasp-stop   Manage the GRASP server (port 6789)
│
└── pipeline TTL_DIR               Run everything: merge → index → start → views → export → stop
```

---

## Project layout

### Repository

| Path                                        | Purpose                                                                                                                |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `src/europeana_qlever/`                     | Python CLI source                                                                                                      |
| `src/europeana_qlever/schema/edm.yaml`      | EDM base schema — primary source of truth for the data model (12 classes, 242 attributes)                              |
| `src/europeana_qlever/schema/edm_parquet.yaml` | Export schema — declares all 38 export tables as LinkML classes with SPARQL patterns and pipeline annotations       |
| `src/europeana_qlever/ask/`                 | NL→SQL / NL→SPARQL agents, EDM domain notes, benchmark runner                                                          |
| `src/europeana_qlever/explorer/`            | Browser explorer — threaded HTTP server + bundled SPA (vendored offline)                                               |
| `src/europeana_qlever/grasp/`               | Bundled GRASP resource files (SPARQL templates, prefix mappings)                                                       |
| `src/europeana_qlever/report_questions/`    | Bundled report YAML files (edit in place to customise)                                                                 |
| `references/ontologies/`                    | Vendored upstream ontology files (metis-schema XSD/OWL + cached external ontologies)                                   |
| `references/vocabularies/metis-vocabularies/` | Europeana's Metis vocabulary registry (authority URI patterns, source of truth for `x_authority`)                    |
| `scripts/update-*.py`                       | Standalone uv scripts for regenerating schemas and syncing references                                                  |
| `docs/europeana/`                           | Europeana KB exported from Confluence + `EDM.md` narrative reference                                                   |
| `docs/qlever/docs/`                         | QLever documentation (mirrored from upstream)                                                                          |

### Work directory (`-d <work-dir>`)

| Path                  | Contents                                                                                                          |
| --------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `ttl-merged/`         | Merged TTL chunks (~5 GB each)                                                                                    |
| `index/`              | `Qleverfile`, `settings.json`, and the QLever index files                                                         |
| `exports/`            | Parquet output — `<name>.parquet` for values/composites; `<name>/x_property=<col>/data.parquet` for links_* tables |
| `analysis/`           | Query performance reports (Markdown)                                                                              |
| `reports/`            | Quality/coverage report output (JSON + Markdown)                                                                  |
| `grasp/`              | GRASP runtime config and search indices                                                                           |
| `telemetry.jsonl`     | Structured JSONL log of command spans, resource samples, and stage events                                         |
| `pipeline_state.json` | Pipeline checkpoint for resume-on-failure                                                                         |

---

## Updating schemas & docs

The EDM schema, vendored ontologies, the Metis vocabulary registry, and the local doc sets are all kept fresh via standalone uv scripts:

```bash
uv run scripts/update-all.py                    # everything, in dependency order
uv run scripts/update-edm-schema.py             # regenerate schema/edm.yaml
uv run scripts/update-metis-vocabularies.py     # sync Metis vocabulary registry
uv run scripts/update-qlever-docs.py            # sync QLever docs from GitHub
uv run scripts/update-europeana-docs.py         # sync Europeana KB from Confluence (incremental)
```

`update-all.py` accepts `--only NAME [...]` and `--skip NAME [...]`.

---

## Refreshing the data

Europeana refreshes the FTP dump weekly. To update locally:

```bash
rclone -P copy europeana:dataset/TTL/ ~/data/europeana/TTL/ --transfers=10
uv run europeana-qlever -d /data/europeana pipeline ~/data/europeana/TTL
```

QLever does not support incremental updates, so a refresh is a full re-merge + re-index. The `pipeline` checkpoint will skip stages whose output already exists; pass `--force` to start from scratch.

---

## License

[Apache 2.0](LICENSE)
