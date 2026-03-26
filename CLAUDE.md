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
  constants.py                    # EDM namespaces, QLever settings, rights URIs, monitor thresholds
  merge.py                        # Parallel TTL extraction + rdflib prefix discovery
  export.py                       # QLever HTTP streaming + DuckDB Parquet conversion
  monitor.py                      # Background resource monitor (memory, disk, backpressure)
  query.py                        # Dynamic SPARQL query generator (QueryBuilder, QueryFilters)
tests/
  test_query.py                   # Unit tests for query generation
EDM.md                            # Europeana Data Model reference (EDM, entities, rights)
README.md                         # General-purpose project README
```

Note: source lives under `src/europeana_qlever/` (src layout), mapped in `pyproject.toml` via `[tool.hatch.build.targets.wheel] packages = ["src/europeana_qlever"]`.

### Work directory layout (not in repo)

All output lives under a single work directory specified via `-d` / `--work-dir` (or `EUROPEANA_QLEVER_WORK_DIR` env var). Subdirectory names are defined in `constants.py`.

| Subdirectory | Constant | Purpose |
|--------------|----------|---------|
| `ttl-merged/` | `MERGED_SUBDIR` | Merged chunk TTL files (~5 GB each) |
| `index/` | `INDEX_SUBDIR` | Qleverfile, settings.json, QLever index files |
| `exports/` | `EXPORTS_SUBDIR` | Parquet output files (TSV intermediates are deleted) |
| `monitor.log` | — | CSV resource monitor log (RSS, available memory, disk free) |

The source TTL ZIP directory is user-managed and passed as a positional argument to `merge` and `scan-prefixes`.

## Commands to know

```bash
uv sync                                                         # Install dependencies
uv run europeana-qlever --help                                   # Show all CLI commands
uv run europeana-qlever -d WORK_DIR merge TTL_DIR                # Merge TTL ZIPs into chunks
uv run europeana-qlever -d WORK_DIR write-qleverfile             # Generate Qleverfile + settings.json
uv run europeana-qlever -d WORK_DIR index                        # Build QLever index
uv run europeana-qlever -d WORK_DIR start                        # Start SPARQL server on :7001
uv run europeana-qlever -d WORK_DIR stop                         # Stop SPARQL server
uv run europeana-qlever -d WORK_DIR list-queries                 # List all 36 available queries
uv run europeana-qlever -d WORK_DIR export --all                 # Export all base queries to Parquet
uv run europeana-qlever -d WORK_DIR export --query-set all       # Export all 36 queries
uv run europeana-qlever -d WORK_DIR export -q items_enriched     # Export a specific named query
uv run europeana-qlever -d WORK_DIR export FILE.sparql           # Export a custom .sparql file
uv run europeana-qlever -d WORK_DIR pipeline TTL_DIR             # Run full pipeline end-to-end
uv run pytest tests/test_query.py                                # Run query generator tests
```

All commands require `-d WORK_DIR` (or `EUROPEANA_QLEVER_WORK_DIR` env var). Output paths are derived automatically. Always use `uv run` — never bare `python` or `pip install`.

## Architecture notes

- **Merge** is I/O-bound: uses `ThreadPoolExecutor` (default 4 workers) for parallel ZIP extraction. Workers stream line-by-line from ZIP entries to temp files on disk — never holding more than one line in memory — then a writer thread copies temp files into chunked output files in 1 MB reads. A semaphore (`workers * 2`) bounds in-flight work. Per-file `@prefix`/`@base` lines are stripped and replaced with a unified prefix header per chunk. Temp files live in `output_dir/.merge_tmp/` and are cleaned up automatically.
- **MD5 checksums** are skipped by default (`--checksum-policy=skip`) because the Europeana FTP md5sum files are unreliable. Of ~2,300 md5sum files tested (March 2026), only 7% match their companion ZIPs. The FTP server appears to regenerate md5sum files from freshly built ZIPs that are never actually published (stale checksums), and also strips leading zeros from hex hashes (126 files affected). The `validate` command's `--no-checksums` flag and the merge/pipeline `--checksum-policy` option control this behavior.
- **Prefix discovery** samples ~50 ZIPs via rdflib to catch non-standard prefixes. Falls back to regex if rdflib fails on a file. The canonical EDM prefix set is in `constants.py` as `EDM_PREFIXES`.
- **Export** streams multi-GB SPARQL results via httpx (chunked reads, never loaded into memory), writes TSV, converts to Parquet with DuckDB (`zstd` compression, explicit `memory_limit="4GB"`, spill-to-disk via `temp_directory`), then deletes the intermediate TSV.
- **Resource monitoring** (`monitor.py`): `ResourceMonitor` runs as a daemon thread, sampling process RSS, system available memory, and disk free space every 5 seconds. Samples are logged to `monitor.log` (CSV format). Console warnings fire on state transitions at 80% (warn) and 90% (critical) system memory usage. The merge phase uses `monitor.is_memory_critical()` and `monitor.wait_for_memory()` as a backpressure mechanism — pausing new ZIP submissions when memory is under pressure. Thresholds are configurable in `constants.py` (`MONITOR_WARN_MEMORY_PCT`, `MONITOR_CRITICAL_MEMORY_PCT`).
- **Query generation** (`query.py`) uses `QueryBuilder` to dynamically generate SPARQL queries from composable fragments. `QueryFilters` dataclass carries filter parameters (country, type, rights category, year range, etc.). Queries are grouped into base (7), AI dataset (5), and analytics (24) categories — 36 total. The builder produces `dict[str, str]` consumed by `export_all()`.
- **Qleverfile generation** supports both native (compiled from source) and Docker modes. Native is preferred for performance. Default memory settings: stxxl 8G, query 10G, cache 5G.
- **Pipeline** (`pipeline` command) runs all stages end-to-end: merge → write-qleverfile → index → start → export → stop. Supports `--skip-merge` and `--skip-index` flags. The entire pipeline runs inside a `ResourceMonitor` context for continuous resource tracking.
- Export queries are generated by `QueryBuilder` in `query.py`. The `export --all` flag runs all base queries; `--query-set` runs a category; `-q` runs individual named queries. Custom `.sparql` file paths can also be passed.

## Europeana EDM domain context

For comprehensive documentation on the Europeana Data Model, entity relationships, RDF namespaces, and rights framework, see `EDM.md`. Use it as the primary reference for any questions about the EDM or Europeana at large.

The data follows the **Europeana Data Model (EDM)**. Key entities:

- **ProvidedCHO** — the cultural heritage object
- **ore:Proxy** — descriptive metadata (there's a provider proxy and a Europeana proxy per item)
- **ore:Aggregation** — links to digital representations (WebResources)
- **edm:Agent**, **edm:Place**, **skos:Concept**, **edm:TimeSpan** — contextual entities

The provider proxy (identified by `FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" }`) holds the primary descriptive metadata (dc:title, dc:creator, etc.). The Europeana proxy (`edm:europeanaProxy "true"`) holds normalised enrichments (edm:year).

### QueryBuilder and QueryFilters

`QueryBuilder` generates all SPARQL queries via composable fragment methods (`_provider_proxy()`, `_aggregation()`, `_rights_category_bind()`, etc.). `QueryFilters` is a dataclass with optional filter fields (countries, types, rights_category, year_from/to, limit, etc.) that are injected as FILTER clauses. Rights URIs are classified into "open", "restricted", and "permission" categories using STRSTARTS/CONTAINS patterns in the `_rights_category_bind()` fragment. Constants for rights URI lists and labels live in `constants.py`.

**Language resolution** uses a parallel English + vernacular model. Item-level properties (dc:title, dc:description) produce separate English and vernacular columns plus a COALESCE-resolved fallback. The vernacular language is bound from `dc:language` on the provider proxy. Entity labels (skos:prefLabel) use a simpler chain: en → user extras → any. Users add languages via `QueryBuilder(languages=[...])` or the `--language` CLI flag, which produces extra output columns. Base queries expose only the resolved column; AI queries expose all parallel columns.

## Conventions

- All data-processing logic is in the Python CLI. No bash scripts for pipeline steps.
- CLI commands are in `cli.py`, business logic in `merge.py`/`export.py`/`query.py`, configuration in `constants.py`.
- Use `rich.console.Console` for all terminal output (not bare `print`).
- Click options use `Path` type with `path_type=Path`.
