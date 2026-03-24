# Ingesting Full Europeana TTL Metadata into QLever on DGX Spark

**Purpose:** Step-by-step architecture for loading all ~66 million Europeana EDM records (Turtle format) into a QLever SPARQL engine, enabling large-scale queries with TSV/CSV export for subsequent Parquet conversion.

**Target hardware:** NVIDIA DGX Spark — ARM64 (aarch64), GB10, 128 GB unified LPDDR5x, 4 TB NVMe, Ubuntu 24.04.

**Tooling:** All data-processing steps use the `europeana-qlever` Python CLI (click + rich + rdflib + httpx + duckdb), managed via `uv`. No bash scripts. Docker is assumed pre-installed.

---

## 0. Sizing Estimates

Before setup, it's important to understand what you're loading.

| Metric | Estimate | Reasoning |
|--------|----------|-----------|
| Records | ~66 million | Europeana's published count |
| Triples per record | ~30–80 | CHO + 2 proxies + aggregation + EuropeanaAggregation + WebResource(s) + contextual entities |
| **Total triples** | **~2–5 billion** | Conservative: 66M × 40 avg. Likely closer to 3B based on typical EDM record complexity |
| Compressed TTL on FTP | ~50–120 GB | 15,000+ ZIP files in `TTL/` directory |
| Uncompressed TTL | ~200–500 GB | Turtle is verbose with full URIs; EDM uses many namespaces |
| QLever index size | ~100–250 GB | QLever indexes are typically 0.5–1× the uncompressed input size |
| RAM needed for indexing | ~20–30 GB | Well within 128 GB; QLever indexes Wikidata (20B triples) with ~20 GB |
| Indexing time | ~1–3 hours | At ~1B triples/hour on modern hardware; ARM64 may be ~30% slower than x86 Ryzen |
| RAM for query serving | ~10–20 GB | Depends on query complexity and cache settings |

**Disk budget on 4 TB NVMe:**

| Component | Size |
|-----------|------|
| Compressed TTL ZIPs | ~80 GB |
| Merged uncompressed TTL | ~300 GB |
| QLever index | ~200 GB |
| Working space / query scratch | ~200 GB |
| **Total** | **~780 GB** — comfortably within 4 TB |

---

## 1. ARM64 Platform Considerations

QLever provides native packages for Debian/Ubuntu and Docker images. However, as of early 2026, the pre-built Docker image (`adfreiburg/qlever`) targets `linux/amd64`. On your ARM64 DGX Spark, you have two options:

### Option A: Compile from source (recommended for performance)

QLever is pure C++17 with standard dependencies (Boost, ICU, zstd, etc.). It compiles cleanly on ARM64 Ubuntu 24.04. This gives you native performance with no emulation overhead — critical for a multi-hour indexing job.

### Option B: Docker with QEMU emulation (fallback)

Docker on Ubuntu 24.04 supports running `amd64` images under QEMU user-mode emulation via `binfmt_misc`. This works but indexing will be **5–10× slower** due to instruction translation. Not recommended for 3B+ triples.

### Option C: Check for native ARM64 .deb packages

QLever's GitHub README mentions native packages for Debian/Ubuntu. Check whether ARM64 builds exist:

```bash
# Check the QLever package repository (URL from docs.qlever.dev)
# If arm64 .deb files are available, this is the easiest path
```

**This guide assumes Option A (compile from source)** as the primary path.

---

## 2. Prerequisites — Install Build Dependencies

Docker is assumed pre-installed.

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install build tools for QLever
sudo apt install -y \
  build-essential cmake ninja-build git \
  libboost-all-dev libicu-dev libzstd-dev \
  libjemalloc-dev pkg-config python3 python3-pip \
  wget curl

# Install uv (Python project manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the qlever CLI tool
uv tool install qlever

# Verify
qlever --help
```

---

## 3. Clone and Build QLever from Source

```bash
# Create a working area on the NVMe
mkdir -p ~/dev/qlever
cd ~/dev/qlever

# Clone with submodules
git clone --recursive -j8 https://github.com/ad-freiburg/qlever qlever-code
cd qlever-code

# Build (adjust -j for your 20 ARM cores)
mkdir build && cd build
cmake -GNinja -DCMAKE_BUILD_TYPE=Release ..
ninja -j16
# This takes 10–20 minutes on the DGX Spark's 20-core ARM CPU

# Verify the binaries exist
ls -la ./qlever-index
ls -la ./qlever-server

# Note the binary directory for the Qleverfile
export QLEVER_BIN_DIR=$(pwd)
echo "QLever binaries at: $QLEVER_BIN_DIR"
```

If the build fails on ARM64 due to any architecture-specific issues, check `https://github.com/ad-freiburg/qlever/issues` for patches. QLever's codebase is architecture-portable C++17.

---

## 4. Install the europeana-qlever CLI

All data-processing steps — TTL merging, Qleverfile generation, QLever lifecycle management, SPARQL export, and Parquet conversion — are handled by a single Python CLI. It uses click for commands, rich for progress tracking, rdflib for RDF namespace handling, httpx for streaming HTTP, and DuckDB for Parquet conversion.

```bash
cd ~/dev/europeana-qlever

# Install in development mode with uv
uv sync

# Verify
uv run europeana-qlever --help
```

You should see:

```
Usage: europeana-qlever [OPTIONS] COMMAND [ARGS]...

  Europeana EDM → QLever → Parquet pipeline.

Commands:
  scan-prefixes    Discover all RDF prefixes used across the TTL dump.
  merge            Merge all Europeana TTL ZIPs into chunked TTL files.
  write-qleverfile Generate a Qleverfile configured for the Europeana dataset.
  index            Build the QLever index from merged TTL chunks.
  start            Start the QLever SPARQL server.
  export           Export SPARQL query results from QLever as Parquet files.
```

### CLI Architecture

```
europeana-qlever
├── scan-prefixes     # rdflib-based prefix discovery from sample of ZIPs
├── merge             # Parallel ZIP extraction + chunked TTL output
├── write-qleverfile  # Generate Qleverfile with EDM-optimised settings
├── index             # Build QLever index (wraps qlever CLI)
├── start             # Start QLever SPARQL server
└── export            # SPARQL → TSV (httpx streaming) → Parquet (DuckDB)
```

**Source layout:**

| File | Purpose |
|------|---------|
| `europeana_qlever/__init__.py` | Package metadata |
| `europeana_qlever/cli.py` | Click command definitions |
| `europeana_qlever/constants.py` | Paths, EDM namespaces, QLever settings, SPARQL queries |
| `europeana_qlever/merge.py` | Parallel TTL extraction with rdflib prefix discovery |
| `europeana_qlever/export.py` | QLever HTTP streaming + DuckDB Parquet conversion |

**Default directory layout:**

| Directory | Purpose |
|-----------|---------|
| `~/dev/europeana-qlever/` | Python CLI, Qleverfile, and index files |
| `~/data/europeana/metadata/TTL/` | Downloaded ZIP files from Europeana FTP |
| `~/data/europeana/metadata/TTL-merged/` | Merged chunk TTL files |
| `~/europeana-exports/` | TSV + Parquet output files |

---

## 5. Download the Europeana TTL Bulk Dump

The full TTL dump lives at `ftp://download.europeana.eu/dataset/TTL/` — anonymous FTP, ~15,000+ ZIP files. The Europeana FTP remote is already configured in rclone as `europeana`.

```bash
# Run in tmux (this will take several hours)
tmux new -s download

rclone copy europeana:dataset/TTL/ ~/data/europeana/metadata/TTL/ \
  --progress \
  --transfers=10 \
  --checkers=8 \
  -v
```

**Verify download integrity:**

```bash
cd ~/data/europeana/metadata/TTL
for md5file in *.md5sum; do
  md5sum -c "$md5file" 2>/dev/null || echo "FAILED: $md5file"
done
```

---

## 6. Merge TTL Files

The merge step does two things:

1. **Prefix discovery (rdflib):** Samples ~50 ZIPs, parses ~150 individual TTL records through rdflib to collect every `@prefix` declaration in the corpus. Merges these with the known EDM namespace set so no triple is lost at index time.

2. **Parallel extraction (ThreadPoolExecutor):** Reads each ZIP with 8+ I/O threads, strips per-file `@prefix`/`@base` lines, and writes raw triple lines into chunked output files (~5 GB each), each starting with the unified prefix header.

```bash
cd ~/dev/europeana-qlever

# Full merge with prefix discovery (recommended)
uv run europeana-qlever merge

# Or with custom options:
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

**Expected output (1–3 hours):**

```
Phase 1/2 · Scanning prefixes from sample…
Scanning prefixes ━━━━━━━━━━━━━━━━━━━━ 50/50  0:01:12
Prefix scan complete. 20 canonical + 1 extra = 21 total

Phase 2/2 · Merging 15,234 ZIPs (chunk ≈ 5.0 GB, 12 workers)…
Merging ━━━━━━━━━━━━━━━━━━━━━━ 15,234/15,234 · 1:47:23 · 0:00:00

Done. 15,234 ZIPs → 62 chunk(s) (308.4 GB) in ~/data/europeana/metadata/TTL-merged
  europeana_0000.ttl  (5.00 GB)
  europeana_0001.ttl  (5.00 GB)
  ...
```

> **Why rdflib for prefix discovery:** Each per-record TTL file contains its own
> `@prefix` declarations. When merging, we strip these and provide a unified
> prefix block at the top of each chunk. If any record uses a prefix not in our
> master set, those triples would fail to parse at index time. Sampling via
> rdflib catches these edge cases automatically.
>
> We do NOT parse every record through rdflib (that would take weeks for 66M
> files). The actual extraction uses fast byte-level string ops in parallel
> workers.

---

## 7. Write the Qleverfile

```bash
cd ~/dev/europeana-qlever

uv run europeana-qlever write-qleverfile \
  --qlever-bin ~/dev/qlever/qlever-code/build
```

This writes a `Qleverfile` and `settings.json` into `~/dev/europeana-qlever/europeana-index/` with these EDM-optimised settings:

| Setting | Value | Why |
|---------|-------|-----|
| `languages-internal: []` | All languages kept | Europeana is deeply multilingual (30+ languages); we want all `xml:lang` tags preserved |
| `prefixes-external` | Proxy/aggregation/item URIs | These long, repetitive URIs dominate the dataset. Storing them externally optimizes index compression |
| `ascii-prefixes-only: false` | Allow Unicode prefixes | Europeana literals include diacritics, Cyrillic, Greek, etc. |
| `num-triples-per-batch: 5000000` | 5M triples/batch | Good balance for ~3B triples; keeps RAM usage moderate |
| `STXXL_MEMORY: 15G` | 15 GB for external sorting | Generous within 128 GB budget; speeds up permutation building |
| `MEMORY_FOR_QUERIES: 20G` | 20 GB for queries | Allows large intermediate results for SPARQL queries over the full graph |
| `CACHE_MAX_SIZE: 10G` | 10 GB query cache | Caches frequent query patterns; good for repeated analytical queries |
| `SYSTEM: native` | No Docker | Direct ARM64 execution; no emulation overhead |

---

## 8. Build the Index

```bash
cd ~/dev/europeana-qlever

# Run in tmux (this takes 2–5 hours)
tmux new -s indexing

uv run europeana-qlever index
```

The command delegates to the `qlever` CLI, streaming all output to the terminal and to `europeana-index.log` in the index directory.

**Expected indexing phases and approximate times (on DGX Spark):**

| Phase | Time | Notes |
|-------|------|-------|
| Parse input | ~40–90 min | Reading and parsing all TTL; I/O bound |
| Build vocabularies | ~15–30 min | Building subject/predicate/object dictionaries |
| Convert to global IDs | ~10–20 min | Mapping local to global identifiers |
| Permutation SPO & SOP | ~20–40 min | Building sort permutations |
| Permutation OSP & OPS | ~25–50 min | |
| Permutation PSO & POS | ~25–50 min | |
| **Total** | **~2.5–5 hours** | ARM64 may be ~30–50% slower than x86 benchmarks |

---

## 9. Start the QLever Server

```bash
cd ~/dev/europeana-qlever

uv run europeana-qlever start
```

**Verify with a basic query:**

```bash
curl -Gs http://localhost:7001 \
  --data-urlencode 'query=SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }' \
  --data-urlencode 'action=tsv_export'
```

This returns the total triple count — expect a number in the range of 2–5 billion.

---

## 10. Launch the QLever UI (Optional but Useful)

Docker is assumed pre-installed.

```bash
cd ~/dev/qlever
git clone https://github.com/ad-freiburg/qlever-ui.git
cd qlever-ui

# Build the UI Docker image (small Python/JS app, runs fine under QEMU)
docker build -t qlever-ui .

# Start the UI
docker run -d \
  --name qlever-ui \
  -p 7000:7000 \
  --restart unless-stopped \
  qlever-ui

# Access at http://localhost:7000
# Configure it to point to http://localhost:7001 as the backend
```

---

## 11. Export to Parquet

The `export` command streams SPARQL results from QLever via httpx (handles multi-GB responses without loading into memory), writes TSV, then converts to Parquet with zstd compression via DuckDB.

```bash
cd ~/dev/europeana-qlever

# List available queries
uv run europeana-qlever export --list-queries

# Export specific queries
uv run europeana-qlever export --query core_metadata --query agents

# Export everything (all pre-defined queries)
uv run europeana-qlever export

# Skip queries whose .parquet already exists
uv run europeana-qlever export --skip-existing --timeout 7200
```

### Pre-defined queries

| Name | Description | Key variables |
|------|-------------|---------------|
| `core_metadata` | Title, creator, date, type, subject, language, rights, country, data provider | `?item ?title ?creator ?date ?type ?subject ?language ?rights ?country ?dataProvider` |
| `web_resources` | Digital representation URLs with MIME type, dimensions, file size | `?item ?url ?mime ?width ?height ?bytes` |
| `agents` | People/orgs with multilingual labels, dates, profession, Wikidata links | `?agent ?name ?lang ?birth ?death ?profession ?wikidata` |
| `places` | Locations with coordinates, labels, Wikidata links | `?place ?name ?lang ?lat ?lon ?wikidata` |
| `concepts` | SKOS concepts with hierarchy, scheme, cross-scheme matches | `?concept ?label ?lang ?scheme ?broader ?exactMatch` |
| `rights_and_providers` | Item-level rights statements with provider, country, completeness score | `?item ?rights ?dataProvider ?provider ?country ?completeness` |

### Adding custom queries

Add new entries to `EXPORT_QUERIES` in `europeana_qlever/constants.py`:

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

Then export it: `uv run europeana-qlever export --query my_custom_export`

### Key query patterns for Europeana EDM in QLever

**Get provider proxy metadata (the "main" descriptive record):**

```sparql
PREFIX ore: <http://www.openarchives.org/ore/terms/>
PREFIX edm: <http://www.europeana.eu/schemas/edm/>
PREFIX dc:  <http://purl.org/dc/elements/1.1/>

SELECT ?item ?title ?creator ?date ?type ?subject ?language
WHERE {
  ?proxy ore:proxyFor ?item .
  FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" }
  ?proxy dc:title ?title .
  ?proxy edm:type ?type .
  OPTIONAL { ?proxy dc:creator ?creator }
  OPTIONAL { ?proxy dc:date ?date }
  OPTIONAL { ?proxy dc:subject ?subject }
  OPTIONAL { ?proxy dc:language ?language }
}
```

**Get WebResource technical metadata:**

```sparql
PREFIX edm:     <http://www.europeana.eu/schemas/edm/>
PREFIX ebucore: <http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#>

SELECT ?item ?webresource ?mime ?width ?height ?filesize
WHERE {
  ?agg edm:aggregatedCHO ?item ;
       edm:isShownBy ?webresource .
  OPTIONAL { ?wr ebucore:hasMimeType ?mime . FILTER(?wr = ?webresource) }
  OPTIONAL { ?wr ebucore:width ?width . FILTER(?wr = ?webresource) }
  OPTIONAL { ?wr ebucore:height ?height . FILTER(?wr = ?webresource) }
  OPTIONAL { ?wr ebucore:fileByteSize ?filesize . FILTER(?wr = ?webresource) }
}
```

**Get contextual entities (agents with birth/death dates):**

```sparql
PREFIX edm:    <http://www.europeana.eu/schemas/edm/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
PREFIX rdaGr2: <http://rdvocab.info/ElementsGr2/>
PREFIX owl:    <http://www.w3.org/2002/07/owl#>

SELECT ?agent ?name ?birth ?death ?wikidata
WHERE {
  ?agent a edm:Agent ;
         skos:prefLabel ?name .
  FILTER(LANG(?name) = "en")
  OPTIONAL { ?agent rdaGr2:dateOfBirth ?birth }
  OPTIONAL { ?agent rdaGr2:dateOfDeath ?death }
  OPTIONAL {
    ?agent owl:sameAs ?wikidata .
    FILTER(STRSTARTS(STR(?wikidata), "http://www.wikidata.org/entity/"))
  }
}
```

### Export formats

| `action` parameter | Format | Use case |
|--------------------|--------|----------|
| `tsv_export` | Tab-separated values | Best for large exports → Parquet |
| `csv_export` | Comma-separated values | When TSV not suitable |
| `json_export` | JSON | Programmatic access |
| (none) | JSON API response | Small result sets, interactive use |

---

## 12. Operational Notes

### Refreshing the data

Europeana refreshes the FTP dump every Sunday. To update:

1. Re-download changed ZIPs: `rclone copy europeana:dataset/TTL/ ~/data/europeana/metadata/TTL/ --progress --transfers=10 --update`
2. Re-merge: `uv run europeana-qlever merge`
3. Re-index: `uv run europeana-qlever index` (QLever does not support incremental updates for bulk loads; full re-index is needed)
4. Restart the server: `uv run europeana-qlever start`

### Memory management

With 128 GB unified memory (shared CPU+GPU), be mindful:

- Indexing peak: ~25–35 GB
- Server steady-state: ~20–30 GB (index mmap'd + query memory + cache)
- Leave headroom for OS and other workloads (LLM inference, etc.)

### Query timeout for very large exports

For queries that scan the full graph (e.g., all 66M items), increase the timeout:

```bash
uv run europeana-qlever export --query core_metadata --timeout 7200
```

### Federated queries

QLever supports `SERVICE` clauses for federated SPARQL. You can enrich Europeana queries with Wikidata:

```sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT ?agent ?name ?wdDescription WHERE {
  ?agent a edm:Agent ; skos:prefLabel ?name ; owl:sameAs ?wd .
  FILTER(STRSTARTS(STR(?wd), "http://www.wikidata.org/entity/"))
  SERVICE <https://query.wikidata.org/sparql> {
    ?wd schema:description ?wdDescription .
    FILTER(LANG(?wdDescription) = "en")
  }
} LIMIT 1000
```

---

## 14. Summary — End-to-End Workflow

```
1. Build QLever from source on DGX Spark (ARM64)        ~/dev/qlever/qlever-code/build/
2. Install europeana-qlever CLI with uv                  ~/dev/europeana-qlever/
3. rclone copy Europeana TTL dump (~80 GB compressed)    ~/data/europeana/metadata/TTL/
4. uv run europeana-qlever merge                         ~/data/europeana/metadata/TTL-merged/
5. uv run europeana-qlever write-qleverfile              ~/dev/europeana-qlever/europeana-index/
6. uv run europeana-qlever index        → ~2–5 hours  → ~200 GB index
7. uv run europeana-qlever start        → SPARQL endpoint on :7001
8. uv run europeana-qlever export       → ~/europeana-exports/*.parquet
9. Upload to HuggingFace with Croissant metadata
```

**Total time from zero to queryable:** ~12–24 hours (download + merge + index).
**Total disk footprint:** ~600–800 GB on the 4 TB NVMe.