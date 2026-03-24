# CLAUDE.md — europeana-qlever

## What this project is

A Python CLI (`europeana-qlever`) that ingests the full Europeana EDM metadata dump (~66M records, 2–5B triples in Turtle) into a QLever SPARQL engine and exports query results as Parquet files. The pipeline: download TTL ZIPs from Europeana FTP → merge into chunked TTL → build QLever index → serve SPARQL endpoint → export to Parquet via DuckDB.

## Tech stack

- **Python 3.11+**, managed with **uv** (not pip)
- **click** for CLI, **rich** for progress/output, **rdflib** for RDF parsing, **httpx** for streaming HTTP, **duckdb** for Parquet conversion, **pyarrow**
- **QLever** as the SPARQL engine (C++, compiled from source or installed natively)
- Build system: **hatchling**

## Project layout

```
pyproject.toml                    # Package metadata, dependencies, entry point
src/europeana_qlever/
  __init__.py                     # Package version
  cli.py                          # Click command definitions (all commands)
  constants.py                    # EDM namespaces, QLever settings
  merge.py                        # Parallel TTL extraction + rdflib prefix discovery
  export.py                       # QLever HTTP streaming + DuckDB Parquet conversion
queries/                          # Pre-defined SPARQL export queries (.sparql files)
README.md                         # General-purpose project README
```

Note: source lives under `src/europeana_qlever/` (src layout), mapped in `pyproject.toml` via `[tool.hatch.build.targets.wheel] packages = ["src/europeana_qlever"]`.

### Work directory layout (not in repo)

All output lives under a single work directory specified via `-w` / `--work-dir` (or `EUROPEANA_QLEVER_WORK_DIR` env var). Subdirectory names are defined in `constants.py`.

| Subdirectory | Constant | Purpose |
|--------------|----------|---------|
| `ttl-merged/` | `MERGED_SUBDIR` | Merged chunk TTL files (~5 GB each) |
| `index/` | `INDEX_SUBDIR` | Qleverfile, settings.json, QLever index files |
| `exports/` | `EXPORTS_SUBDIR` | TSV + Parquet output files |

The source TTL ZIP directory is user-managed and passed as a positional argument to `merge` and `scan-prefixes`.

## Commands to know

```bash
uv sync                                                         # Install dependencies
uv run europeana-qlever --help                                   # Show all CLI commands
uv run europeana-qlever -w WORK_DIR merge TTL_DIR                # Merge TTL ZIPs into chunks
uv run europeana-qlever -w WORK_DIR write-qleverfile             # Generate Qleverfile + settings.json
uv run europeana-qlever -w WORK_DIR index                        # Build QLever index
uv run europeana-qlever -w WORK_DIR start                        # Start SPARQL server on :7001
uv run europeana-qlever -w WORK_DIR export queries/*.sparql      # Export queries to Parquet
```

All commands require `-w WORK_DIR` (or `EUROPEANA_QLEVER_WORK_DIR` env var). Output paths are derived automatically. Always use `uv run` — never bare `python` or `pip install`.

## Architecture notes

- **Merge** is I/O-bound: uses `ThreadPoolExecutor` for parallel ZIP extraction with a batched submission pattern to bound memory. A single writer thread assembles chunks. Per-file `@prefix`/`@base` lines are stripped and replaced with a unified prefix header per chunk.
- **Prefix discovery** samples ~50 ZIPs via rdflib to catch non-standard prefixes. Falls back to regex if rdflib fails on a file. The canonical EDM prefix set is in `constants.py` as `EDM_PREFIXES`.
- **Export** streams multi-GB SPARQL results via httpx (chunked reads, never loaded into memory), writes TSV, then converts to Parquet with DuckDB (`zstd` compression).
- **Qleverfile generation** supports both native (compiled from source) and Docker modes. Native is preferred for performance.
- Export queries live as standalone `.sparql` files in the `queries/` directory. The `export` command reads them directly from disk.

## Europeana EDM domain context

The data follows the **Europeana Data Model (EDM)**. Key entities:

- **ProvidedCHO** — the cultural heritage object
- **ore:Proxy** — descriptive metadata (there's a provider proxy and a Europeana proxy per item)
- **ore:Aggregation** — links to digital representations (WebResources)
- **edm:Agent**, **edm:Place**, **skos:Concept** — contextual entities

The provider proxy (identified by `FILTER NOT EXISTS { ?proxy edm:europeanaProxy "true" }`) holds the primary descriptive metadata (dc:title, dc:creator, etc.).

## Conventions

- All data-processing logic is in the Python CLI. No bash scripts for pipeline steps.
- CLI commands are in `cli.py`, business logic in `merge.py`/`export.py`, configuration in `constants.py`.
- Use `rich.console.Console` for all terminal output (not bare `print`).
- Click options use `Path` type with `path_type=Path`.
