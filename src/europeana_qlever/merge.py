"""Merge Europeana per-record TTL ZIPs into chunked, QLever-ready TTL files.

Strategy
--------
1. **scan_prefixes** — Sample a subset of ZIPs and use rdflib to parse
   individual TTL files, collecting every @prefix declaration. This catches
   provider-specific prefixes not in the canonical EDM set.
2. **merge** — Process all ZIPs in parallel (ThreadPoolExecutor, I/O-bound).
   Each worker extracts TTL content from a ZIP, strips per-file @prefix and
   @base lines, and returns raw triple bytes. A single writer thread assembles
   the results into chunked output files, each prepended with the master
   prefix block.

The merge is intentionally streaming: workers yield bytes through a queue so
that memory stays bounded even with 15,000+ ZIPs.
"""

from __future__ import annotations

import io
import logging
import os
import re
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from queue import Queue

import rdflib
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from .constants import EDM_PREFIXES

console = Console()

# Matches @prefix and @base declarations at the start of a line
_PREFIX_RE = re.compile(r"^@(?:prefix|base)\s", re.IGNORECASE)

# Fallback regex to extract prefix declarations without full rdflib parse
_PREFIX_DECL_RE = re.compile(r"@prefix\s+(\S+):\s+<([^>]+)>")


# ---------------------------------------------------------------------------
# Prefix block generation
# ---------------------------------------------------------------------------

def generate_prefix_block(prefixes: dict[str, str]) -> str:
    """Render a Turtle prefix block from a {prefix: namespace_uri} dict."""
    lines = [f"@prefix {p}: <{u}> ." for p, u in sorted(prefixes.items())]
    return "\n".join(lines) + "\n\n"


# ---------------------------------------------------------------------------
# Prefix discovery (uses rdflib for robust parsing)
# ---------------------------------------------------------------------------

def scan_prefixes_from_sample(
    ttl_dir: Path,
    sample_size: int = 50,
    files_per_zip: int = 3,
) -> dict[str, str]:
    """Scan a sample of ZIPs to discover all RDF prefixes used in the dataset.

    Starts with the canonical EDM prefix set and adds any extras found via
    rdflib parsing. Falls back to regex extraction if rdflib chokes on a file.

    Parameters
    ----------
    ttl_dir : Path
        Directory containing Europeana .zip files with per-record TTL.
    sample_size : int
        How many ZIP files to sample.
    files_per_zip : int
        How many TTL files to parse inside each sampled ZIP.

    Returns
    -------
    dict[str, str]
        Merged prefix → namespace URI mapping.
    """
    discovered: dict[str, str] = dict(EDM_PREFIXES)
    known_uris = set(discovered.values())

    zip_files = sorted(ttl_dir.glob("*.zip"))
    if not zip_files:
        console.print(f"[yellow]No .zip files found in {ttl_dir}[/yellow]")
        return discovered

    sample = zip_files[:sample_size]
    parse_errors = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning prefixes", total=len(sample))

        for zp in sample:
            try:
                with zipfile.ZipFile(zp) as zf:
                    ttl_names = [n for n in zf.namelist() if n.endswith(".ttl")]
                    for name in ttl_names[:files_per_zip]:
                        raw = zf.read(name)
                        text = raw.decode("utf-8", errors="replace")

                        # Try rdflib first (robust namespace extraction)
                        try:
                            g = rdflib.Graph()
                            # Suppress rdflib warnings about malformed literals
                            # (e.g. odd-length xsd:hexBinary values in Europeana data)
                            _rdflib_logger = logging.getLogger("rdflib.term")
                            _prev_level = _rdflib_logger.level
                            _rdflib_logger.setLevel(logging.ERROR)
                            try:
                                g.parse(data=text, format="turtle")
                            finally:
                                _rdflib_logger.setLevel(_prev_level)
                            for prefix, ns in g.namespaces():
                                uri = str(ns)
                                if prefix and uri not in known_uris:
                                    discovered[str(prefix)] = uri
                                    known_uris.add(uri)
                        except Exception:
                            # Fallback: regex extraction of @prefix lines
                            parse_errors += 1
                            for match in _PREFIX_DECL_RE.finditer(text):
                                p, u = match.group(1), match.group(2)
                                if u not in known_uris:
                                    discovered[p] = u
                                    known_uris.add(u)
            except (zipfile.BadZipFile, OSError) as exc:
                console.print(f"[yellow]Skipping {zp.name}: {exc}[/yellow]")

            progress.advance(task)

    extra = len(discovered) - len(EDM_PREFIXES)
    console.print(
        f"[green]Prefix scan complete.[/green] "
        f"{len(EDM_PREFIXES)} canonical + {extra} extra = {len(discovered)} total"
    )
    if parse_errors:
        console.print(
            f"[yellow]{parse_errors} file(s) fell back to regex parsing[/yellow]"
        )
    return discovered


# ---------------------------------------------------------------------------
# Single-ZIP extraction (worker function)
# ---------------------------------------------------------------------------

def _extract_zip(zip_path: Path) -> bytes:
    """Extract all TTL from *zip_path*, stripping prefix/base declarations.

    Returns the concatenated triple content as UTF-8 bytes. Empty bytes on
    error (logged, never raised).
    """
    parts: list[str] = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if not name.endswith(".ttl"):
                    continue
                text = zf.read(name).decode("utf-8", errors="replace")
                lines = [
                    line
                    for line in text.splitlines()
                    if line.strip() and not _PREFIX_RE.match(line)
                ]
                if lines:
                    parts.append("\n".join(lines))
                    parts.append("\n")
    except (zipfile.BadZipFile, OSError) as exc:
        console.print(f"[yellow]Warning: skipping {zip_path.name}: {exc}[/yellow]")
    return "".join(parts).encode("utf-8") if parts else b""


# ---------------------------------------------------------------------------
# Parallel merge
# ---------------------------------------------------------------------------

def merge_ttl(
    ttl_dir: Path,
    output_dir: Path,
    *,
    chunk_size_gb: float = 5.0,
    workers: int = 8,
    prefixes: dict[str, str] | None = None,
) -> list[Path]:
    """Merge all TTL ZIPs into chunked output files with parallel extraction.

    Parameters
    ----------
    ttl_dir : Path
        Directory containing Europeana .zip files.
    output_dir : Path
        Where to write the merged ``europeana_NNNN.ttl`` chunk files.
    chunk_size_gb : float
        Approximate maximum size of each output chunk in gigabytes.
    workers : int
        Number of parallel threads for ZIP extraction.
    prefixes : dict or None
        Prefix map to use. If ``None``, runs ``scan_prefixes_from_sample``
        automatically.

    Returns
    -------
    list[Path]
        Paths to the chunk files that were written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Resolve prefixes
    if prefixes is None:
        console.print("[bold]Phase 1/2 · Scanning prefixes from sample…[/bold]")
        prefixes = scan_prefixes_from_sample(ttl_dir)
    prefix_block = generate_prefix_block(prefixes).encode("utf-8")

    # 2. Enumerate source ZIPs
    zip_files = sorted(ttl_dir.glob("*.zip"))
    if not zip_files:
        console.print(f"[red]No ZIP files found in {ttl_dir}[/red]")
        return []

    console.print(
        f"[bold]Phase 2/2 · Merging {len(zip_files):,} ZIPs "
        f"(chunk ≈ {chunk_size_gb:.1f} GB, {workers} workers)…[/bold]"
    )

    chunk_size_bytes = int(chunk_size_gb * 1_000_000_000)
    chunk_files: list[Path] = []
    chunk_num = 0
    current_size = 0

    def _open_chunk() -> io.BufferedWriter:
        nonlocal chunk_num, current_size
        path = output_dir / f"europeana_{chunk_num:04d}.ttl"
        chunk_files.append(path)
        fh = open(path, "wb")
        fh.write(prefix_block)
        current_size = len(prefix_block)
        return fh

    fh = _open_chunk()

    # Process in batches to bound memory: submit `batch_size` ZIPs at a time
    batch_size = workers * 4

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("·"),
        TimeElapsedColumn(),
        TextColumn("·"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Merging", total=len(zip_files))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            for batch_start in range(0, len(zip_files), batch_size):
                batch = zip_files[batch_start : batch_start + batch_size]
                futures = {pool.submit(_extract_zip, zp): zp for zp in batch}

                for future in as_completed(futures):
                    data = future.result()
                    if data:
                        fh.write(data)
                        current_size += len(data)

                        # Roll over to the next chunk if we've exceeded the limit
                        if current_size >= chunk_size_bytes:
                            fh.close()
                            chunk_num += 1
                            fh = _open_chunk()

                    progress.advance(task)

    fh.close()

    # Summary
    total_bytes = sum(p.stat().st_size for p in chunk_files)
    console.print(
        f"\n[green]Done.[/green] {len(zip_files):,} ZIPs → "
        f"{len(chunk_files)} chunk(s) "
        f"({total_bytes / 1e9:.1f} GB) in {output_dir}"
    )
    for p in chunk_files:
        console.print(f"  {p.name}  ({p.stat().st_size / 1e9:.2f} GB)")

    return chunk_files