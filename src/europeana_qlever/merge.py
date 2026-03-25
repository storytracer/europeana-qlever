"""Merge Europeana per-record TTL ZIPs into chunked, QLever-ready TTL files.

Strategy
--------
1. **scan_prefixes** — Sample a subset of ZIPs and use rdflib to parse
   individual TTL files, collecting every @prefix declaration. This catches
   provider-specific prefixes not in the canonical EDM set.
2. **merge** — Process all ZIPs in parallel (ThreadPoolExecutor, I/O-bound).
   Each worker extracts TTL content from a ZIP, strips per-file @prefix and
   @base lines, and streams filtered lines to a temp file on disk. A single
   writer thread assembles temp files into chunked output files, each
   prepended with the master prefix block.

Memory efficiency: workers write to temp files (one line in memory at a time),
the writer reads temp files in 1 MB chunks. A semaphore bounds concurrent
in-flight work, and an optional ResourceMonitor provides backpressure when
system memory is under pressure.
"""

from __future__ import annotations

import io
import logging
import os
import re
import shutil
import threading
import zipfile
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path

import rdflib
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from . import display
from .constants import EDM_PREFIXES
from .state import MergeResult
logger = logging.getLogger(__name__)

# Matches @prefix and @base declarations at the start of a line
_PREFIX_RE = re.compile(r"^@(?:prefix|base)\s", re.IGNORECASE)

# Fallback regex to extract prefix declarations without full rdflib parse
_PREFIX_DECL_RE = re.compile(r"@prefix\s+(\S+):\s+<([^>]+)>")

# Size of read buffer when copying temp files to chunk files
_COPY_BUF = 1_048_576  # 1 MB


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
        display.console.print(f"[yellow]No .zip files found in {ttl_dir}[/yellow]")
        return discovered

    sample = zip_files[:sample_size]
    parse_errors = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=display.console,
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
                            del g  # prompt GC of parsed graph
                        except Exception:
                            # Fallback: regex extraction of @prefix lines
                            parse_errors += 1
                            for match in _PREFIX_DECL_RE.finditer(text):
                                p, u = match.group(1), match.group(2)
                                if u not in known_uris:
                                    discovered[p] = u
                                    known_uris.add(u)
            except (zipfile.BadZipFile, OSError) as exc:
                display.console.print(f"[yellow]Skipping {zp.name}: {exc}[/yellow]")

            progress.advance(task)

    extra = len(discovered) - len(EDM_PREFIXES)
    display.console.print(
        f"[green]Prefix scan complete.[/green] "
        f"{len(EDM_PREFIXES)} canonical + {extra} extra = {len(discovered)} total"
    )
    if parse_errors:
        display.console.print(
            f"[yellow]{parse_errors} file(s) fell back to regex parsing[/yellow]"
        )
    return discovered


# ---------------------------------------------------------------------------
# Single-ZIP extraction (worker function — streams to temp file)
# ---------------------------------------------------------------------------

def _extract_zip_to_file(zip_path: Path, output_file: Path) -> int:
    """Extract all TTL from *zip_path*, stripping prefix/base declarations.

    Streams line-by-line to *output_file* so that memory usage is bounded
    to a single line at a time. Returns bytes written, or 0 on error.
    """
    bytes_written = 0
    try:
        with open(output_file, "wb") as out:
            with zipfile.ZipFile(zip_path) as zf:
                for name in zf.namelist():
                    if not name.endswith(".ttl"):
                        continue
                    with zf.open(name) as entry:
                        for raw_line in entry:
                            line = raw_line.decode("utf-8", errors="replace")
                            if line.strip() and not _PREFIX_RE.match(line):
                                out.write(raw_line)
                                bytes_written += len(raw_line)
    except (zipfile.BadZipFile, OSError) as exc:
        display.console.print(f"[yellow]Warning: skipping {zip_path.name}: {exc}[/yellow]")
        # Clean up partial temp file
        try:
            output_file.unlink(missing_ok=True)
        except OSError:
            pass
    return bytes_written


# ---------------------------------------------------------------------------
# Parallel merge
# ---------------------------------------------------------------------------

def merge_ttl(
    ttl_dir: Path,
    output_dir: Path,
    *,
    chunk_size_gb: float = 5.0,
    workers: int = 4,
    prefixes: dict[str, str] | None = None,
    monitor: object | None = None,
    skip_zips: frozenset[str] = frozenset(),
) -> MergeResult:
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
    monitor : ResourceMonitor or None
        Optional resource monitor for memory backpressure. When provided
        and memory is critical, new submissions are paused until memory
        recovers.
    skip_zips : frozenset[str]
        ZIP filenames to skip (for resuming a previous merge).

    Returns
    -------
    MergeResult
        Outcome with chunk files, processed/failed ZIP lists, and totals.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Resolve prefixes
    if prefixes is None:
        display.console.print("[bold]Phase 1/2 · Scanning prefixes from sample…[/bold]")
        prefixes = scan_prefixes_from_sample(ttl_dir)
    prefix_block = generate_prefix_block(prefixes).encode("utf-8")

    # 2. Enumerate source ZIPs (filtering out already-processed ones)
    all_zips = sorted(ttl_dir.glob("*.zip"))
    if skip_zips:
        zip_files = [z for z in all_zips if z.name not in skip_zips]
        logger.info(
            "Resuming merge: %d ZIPs total, %d already processed, %d remaining",
            len(all_zips), len(skip_zips), len(zip_files),
        )
        if skip_zips:
            display.console.print(
                f"[dim]Resuming: skipping {len(skip_zips):,} already-processed ZIPs[/dim]"
            )
    else:
        zip_files = all_zips
    if not zip_files:
        display.console.print(f"[red]No ZIP files found in {ttl_dir}[/red]")
        return MergeResult(total_zips=len(all_zips))

    display.console.print(
        f"[bold]Phase 2/2 · Merging {len(zip_files):,} ZIPs "
        f"(chunk ≈ {chunk_size_gb:.1f} GB, {workers} workers)…[/bold]"
    )

    chunk_size_bytes = int(chunk_size_gb * 1_000_000_000)
    chunk_files: list[Path] = []
    chunk_num = 0
    current_size = 0

    # Temp directory for worker output — clean start
    tmp_dir = output_dir / ".merge_tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir()

    def _open_chunk() -> io.BufferedWriter:
        nonlocal chunk_num, current_size
        path = output_dir / f"europeana_{chunk_num:04d}.ttl"
        chunk_files.append(path)
        fh = open(path, "wb")
        fh.write(prefix_block)
        current_size = len(prefix_block)
        return fh

    fh = _open_chunk()

    # Semaphore limits in-flight work (workers extracting + completed awaiting write)
    sem = threading.Semaphore(workers * 2)

    # Track processed/failed ZIPs for result reporting
    processed_zips: list[str] = list(skip_zips)
    failed_zips: list[str] = []
    # Map futures to (tmp_path, zip_path) for failure tracking
    future_meta: dict[Future[int], tuple[Path, Path]] = {}

    def _drain_future(fut: Future[int]) -> None:
        nonlocal current_size, chunk_num, fh
        temp, zp = future_meta.pop(fut)
        bytes_written = fut.result()
        if bytes_written > 0 and temp.exists():
            with open(temp, "rb") as src:
                while buf := src.read(_COPY_BUF):
                    fh.write(buf)
                    current_size += len(buf)
            temp.unlink()
            processed_zips.append(zp.name)

            if current_size >= chunk_size_bytes:
                fh.close()
                chunk_num += 1
                fh = _open_chunk()
        else:
            if temp.exists():
                temp.unlink(missing_ok=True)
            if bytes_written == 0:
                failed_zips.append(zp.name)
                logger.warning("ZIP extraction failed: %s", zp.name)

        sem.release()

    logger.info("Starting merge of %d ZIPs with %d workers", len(zip_files), workers)

    if display.is_narrow():
        _columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
        ]
    else:
        _columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("·"),
            TimeElapsedColumn(),
            TextColumn("·"),
            TimeRemainingColumn(),
        ]

    with Progress(*_columns, console=display.console) as progress:
        task = progress.add_task("Merging", total=len(zip_files))

        with ThreadPoolExecutor(max_workers=workers) as pool:

            for i, zp in enumerate(zip_files):
                # Backpressure: wait if system memory is critical
                if monitor is not None and hasattr(monitor, "is_memory_critical"):
                    if monitor.is_memory_critical():
                        monitor.wait_for_memory(timeout=120)

                # Bound concurrency via semaphore
                sem.acquire()

                tmp_path = tmp_dir / f"{i:06d}.tmp"
                future = pool.submit(_extract_zip_to_file, zp, tmp_path)
                future_meta[future] = (tmp_path, zp)

                # Drain any completed futures to free memory and disk
                done = [f for f in future_meta if f.done()]
                for fut in done:
                    _drain_future(fut)
                    progress.advance(task)

            # Drain remaining futures
            for future in as_completed(future_meta.copy()):
                _drain_future(future)
                progress.advance(task)

    fh.close()

    # Clean up temp directory
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # Summary
    total_bytes = sum(p.stat().st_size for p in chunk_files)
    display.console.print(
        f"\n[green]Done.[/green] {len(zip_files):,} ZIPs → "
        f"{len(chunk_files)} chunk(s) "
        f"({total_bytes / 1e9:.1f} GB) in {display.short_path(output_dir)}"
    )
    for p in chunk_files:
        display.console.print(f"  {p.name}  ({p.stat().st_size / 1e9:.2f} GB)")

    if failed_zips:
        display.console.print(
            f"\n[yellow]{len(failed_zips):,} ZIP(s) failed during merge[/yellow]"
        )
        logger.warning(
            "Merge completed with %d failed ZIPs out of %d",
            len(failed_zips), len(zip_files),
        )

    result = MergeResult(
        chunk_files=chunk_files,
        total_zips=len(all_zips),
        processed_zips=processed_zips,
        failed_zips=failed_zips,
        total_bytes=total_bytes,
    )
    logger.info(
        "Merge complete: %d chunks, %d processed, %d failed, %.1f GB",
        len(chunk_files), len(processed_zips), len(failed_zips),
        total_bytes / 1e9,
    )
    return result
