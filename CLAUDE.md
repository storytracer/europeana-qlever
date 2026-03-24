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
  init.py                         # Package version
  cli.py                          # Click command definitions (all commands)
  constants.py                    # Paths, EDM namespaces, QLever settings, SPARQL queries
  merge.py                        # Parallel TTL extraction + rdflib prefix discovery
  export.py                       # QLever HTTP streaming + DuckDB Parquet conversion
setup-spark.md                    # DGX Spark-specific setup guide (reference, not the README)
README.md                         # General-purpose project README
```

Note: source lives under `src/europeana_qlever/` (src layout), mapped in `pyproject.toml` via `[tool.hatch.build.targets.wheel] packages = ["src/europeana_qlever"]`. The `__init__.py` file is named `init.py` on disk.

### Generated directories (not in repo)

| Directory | Purpose |
|-----------|---------|
| `europeana-index/` | Qleverfile, settings.json, QLever index files |
| `~/data/europeana/metadata/TTL/` | Downloaded ZIP files from Europeana FTP |
| `~/data/europeana/metadata/TTL-merged/` | Merged chunk TTL files (~5 GB each) |
| `~/europeana-exports/` | TSV + Parquet output files |

## Commands to know

```bash
uv sync                                     # Install dependencies
uv run europeana-qlever --help               # Show all CLI commands
uv run europeana-qlever merge                # Merge TTL ZIPs into chunks
uv run europeana-qlever write-qleverfile     # Generate Qleverfile + settings.json
uv run europeana-qlever index                # Build QLever index
uv run europeana-qlever start                # Start SPARQL server on :7001
uv run europeana-qlever export               # Export all queries to Parquet
```

Always use `uv run` to invoke the CLI — never bare `python` or `pip install`.

## Architecture notes

- **Merge** is I/O-bound: uses `ThreadPoolExecutor` for parallel ZIP extraction with a batched submission pattern to bound memory. A single writer thread assembles chunks. Per-file `@prefix`/`@base` lines are stripped and replaced with a unified prefix header per chunk.
- **Prefix discovery** samples ~50 ZIPs via rdflib to catch non-standard prefixes. Falls back to regex if rdflib fails on a file. The canonical EDM prefix set is in `constants.py` as `EDM_PREFIXES`.
- **Export** streams multi-GB SPARQL results via httpx (chunked reads, never loaded into memory), writes TSV, then converts to Parquet with DuckDB (`zstd` compression).
- **Qleverfile generation** supports both native (compiled from source) and Docker modes. Native is preferred for performance.
- Default paths are defined in `constants.py` as `DEFAULT_TTL_SOURCE`, `DEFAULT_MERGED_DIR`, `DEFAULT_INDEX_DIR`, `DEFAULT_EXPORT_DIR`.
- Export queries are defined in `constants.py` as `EXPORT_QUERIES` dict — add new entries there for custom exports.

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
