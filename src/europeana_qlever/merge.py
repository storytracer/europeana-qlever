"""Merge Europeana per-record TTL ZIPs into chunked, QLever-ready TTL files.

Strategy
--------
1. **scan_prefixes** — Sample a subset of ZIPs and use rdflib to parse
   individual TTL files, collecting every @prefix declaration. This catches
   provider-specific prefixes not in the canonical EDM set.
2. **merge** — Process all ZIPs in parallel (ThreadPoolExecutor, I/O-bound).
   Each worker extracts TTL content from a ZIP using a fast two-phase
   approach: line-by-line header stripping then bulk binary copying.
   A dedicated writer thread assembles temp files into chunked output
   files, each prepended with the master prefix block.

Memory efficiency: workers write to temp files (bulk byte copies), the
writer reads temp files in 8 MB chunks. A semaphore bounds concurrent
in-flight work, and an optional ResourceMonitor provides graduated
backpressure when system memory is under pressure.
"""

from __future__ import annotations

import io
import logging
import os
import queue
import re
import shutil
import threading
import time
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
from .constants import DEFAULT_BULK_READ_SIZE, DEFAULT_COPY_BUF_SIZE, EDM_PREFIXES
from .state import MergeResult

logger = logging.getLogger(__name__)

# Matches @prefix and @base declarations at the start of a line
_PREFIX_RE = re.compile(r"^@(?:prefix|base)\s", re.IGNORECASE)

# Fallback regex to extract prefix declarations without full rdflib parse
_PREFIX_DECL_RE = re.compile(r"@prefix\s+(\S+):\s+<([^>]+)>")

# Byte markers for safety check during bulk copy
_PREFIX_MARKER = b"@prefix"
_BASE_MARKER = b"@base"
_STRAY_AT_MARKER = b"\n@ "

# Defense-in-depth: catch lines starting with @ that aren't @prefix or @base
_BAD_AT_LINE_RE = re.compile(r"^@(?!prefix\s|base\s)\S", re.IGNORECASE)


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
# Fallback: line-by-line filtering for entries with stray prefix lines
# ---------------------------------------------------------------------------

def _should_filter_line(line: str) -> bool:
    """Return True if *line* should be stripped from merged output.

    Catches @prefix/@base declarations **and** malformed @ directives
    (e.g. ``@ spa .``) as a defense-in-depth safety net.
    """
    return bool(_PREFIX_RE.match(line) or _BAD_AT_LINE_RE.match(line))


def _fallback_line_filter(
    initial_chunk: bytes,
    entry: io.BufferedIOBase,
    out: io.BufferedWriter,
) -> int:
    """Filter prefix/base/bad-@ lines from *initial_chunk* + rest of *entry*.

    Called when the bulk copy phase detects a stray ``@prefix``, ``@base``,
    or suspicious ``@ `` marker in a read chunk. Switches to line-by-line
    filtering for the remainder of that ZIP entry.

    Returns bytes written.
    """
    bytes_written = 0
    # Process the chunk that triggered the fallback
    for raw_line in initial_chunk.split(b"\n"):
        if not raw_line.strip():
            continue
        line = raw_line.decode("utf-8", errors="replace")
        if _should_filter_line(line):
            continue
        # Re-add newline stripped by split
        data = raw_line + b"\n"
        out.write(data)
        bytes_written += len(data)
    # Continue line-by-line for the rest of the entry
    for raw_line in entry:
        line = raw_line.decode("utf-8", errors="replace")
        if line.strip() and not _should_filter_line(line):
            out.write(raw_line)
            bytes_written += len(raw_line)
    return bytes_written


# ---------------------------------------------------------------------------
# Single-ZIP extraction (worker function — two-phase: header then bulk)
# ---------------------------------------------------------------------------

def _extract_zip_to_file(
    zip_path: Path,
    output_file: Path,
    bulk_read_size: int = DEFAULT_BULK_READ_SIZE,
    skip_entries: frozenset[str] = frozenset(),
) -> int:
    """Extract all TTL from *zip_path*, stripping prefix/base declarations.

    Uses a two-phase approach per TTL entry:
      1. **Header phase**: read lines one at a time, skipping @prefix/@base.
      2. **Bulk phase**: once past the header, copy raw bytes in chunks
         (no decode, no regex) for maximum throughput.

    If a stray @prefix/@base is detected during bulk copy, falls back to
    line-by-line filtering for the remainder of that entry.

    Entries whose names appear in *skip_entries* (populated from the
    validation manifest) are silently skipped.

    Returns bytes written, or 0 on error.
    """
    bytes_written = 0
    try:
        with open(output_file, "wb") as out:
            with zipfile.ZipFile(zip_path) as zf:
                for name in zf.namelist():
                    if not name.endswith(".ttl"):
                        continue
                    if name in skip_entries:
                        logger.debug(
                            "Skipping invalid entry %s:%s (validation)",
                            zip_path.name, name,
                        )
                        continue
                    with zf.open(name) as entry:
                        # Phase 1: skip prefix/base header lines
                        for raw_line in entry:
                            line = raw_line.decode("utf-8", errors="replace")
                            if not line.strip():
                                continue
                            if _PREFIX_RE.match(line):
                                continue
                            # First data line — write it and switch to bulk
                            out.write(raw_line)
                            bytes_written += len(raw_line)
                            break
                        # Phase 2: bulk copy remainder (no decode, no regex)
                        while True:
                            chunk = entry.read(bulk_read_size)
                            if not chunk:
                                break
                            if (
                                _PREFIX_MARKER in chunk
                                or _BASE_MARKER in chunk
                                or _STRAY_AT_MARKER in chunk
                                or chunk.startswith(b"@ ")
                            ):
                                # Rare: stray directive in data — fall back
                                logger.debug(
                                    "Stray @prefix/@base/@ in %s:%s, "
                                    "falling back to line-by-line",
                                    zip_path.name, name,
                                )
                                bytes_written += _fallback_line_filter(
                                    chunk, entry, out,
                                )
                                break
                            out.write(chunk)
                            bytes_written += len(chunk)
    except (zipfile.BadZipFile, OSError) as exc:
        display.console.print(
            f"[yellow]Warning: skipping {zip_path.name}: {exc}[/yellow]"
        )
        # Clean up partial temp file
        try:
            output_file.unlink(missing_ok=True)
        except OSError:
            pass
    return bytes_written


# ---------------------------------------------------------------------------
# Writer thread — drains completed futures into chunk files
# ---------------------------------------------------------------------------

def _writer_loop(
    write_q: queue.Queue,
    chunk_size_bytes: int,
    prefix_block: bytes,
    output_dir: Path,
    chunk_files: list[Path],
    processed_zips: list[str],
    failed_zips: list[str],
    sem: threading.Semaphore,
    progress_cb: callable | None,
    dashboard: object | None,
    error_holder: list,
    copy_buf_size: int = DEFAULT_COPY_BUF_SIZE,
) -> None:
    """Background writer that assembles temp files into chunk output files.

    Reads ``(tmp_path, zip_path, bytes_written)`` tuples from *write_q*.
    A ``None`` sentinel signals shutdown.
    """
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

    try:
        while True:
            item = write_q.get()
            if item is None:
                break
            tmp_path, zip_path, bytes_written = item

            if bytes_written > 0 and tmp_path.exists():
                with open(tmp_path, "rb") as src:
                    shutil.copyfileobj(src, fh, length=copy_buf_size)
                    # Track size from file stat (faster than counting bytes)
                    current_size += tmp_path.stat().st_size
                tmp_path.unlink()
                processed_zips.append(zip_path.name)

                if current_size >= chunk_size_bytes:
                    fh.close()
                    chunk_num += 1
                    fh = _open_chunk()
                    if dashboard is not None:
                        try:
                            dashboard.set_info("chunks", len(chunk_files))
                        except Exception:
                            pass
            else:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)
                if bytes_written == 0:
                    failed_zips.append(zip_path.name)
                    logger.warning("ZIP extraction failed: %s", zip_path.name)

            sem.release()
            if progress_cb is not None:
                progress_cb()

            write_q.task_done()
    except Exception as exc:
        error_holder.append(exc)
        logger.exception("Writer thread crashed")
    finally:
        fh.close()


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
    manifest: dict | None = None,
    dashboard: object | None = None,
    bulk_read_size: int = DEFAULT_BULK_READ_SIZE,
    copy_buf_size: int = DEFAULT_COPY_BUF_SIZE,
    backpressure_thresholds: tuple[float, float, float] = (70.0, 80.0, 90.0),
    backpressure_sleeps: tuple[float, float] = (0.1, 0.5),
    writer_join_timeout: int = 300,
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
        and memory is high, submissions are throttled or paused.
    skip_zips : frozenset[str]
        ZIP filenames to skip (for resuming a previous merge).
    manifest : dict or None
        Validation manifest mapping ``{zip_name: ZipReport}``. When provided,
        invalid entries within each ZIP are skipped during extraction.
    dashboard : Dashboard or None
        Optional dashboard for live progress updates.

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

    # Temp directory for worker output — clean start
    tmp_dir = output_dir / ".merge_tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir()

    # Semaphore limits in-flight work; queue bounds temp disk usage
    sem = threading.Semaphore(workers * 3)

    # Shared state (written only by writer thread)
    processed_zips: list[str] = list(skip_zips)
    failed_zips: list[str] = []

    # Writer queue + thread
    write_q: queue.Queue = queue.Queue(maxsize=max(4, workers * 2))
    writer_errors: list[Exception] = []

    # Activate faster monitoring during merge
    if monitor is not None and hasattr(monitor, "set_active"):
        monitor.set_active(True)

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

        def _progress_cb() -> None:
            progress.advance(task)
            if dashboard is not None:
                try:
                    dashboard.advance()
                except Exception:
                    pass

        # Start writer thread
        writer_thread = threading.Thread(
            target=_writer_loop,
            args=(
                write_q, chunk_size_bytes, prefix_block, output_dir,
                chunk_files, processed_zips, failed_zips,
                sem, _progress_cb, dashboard, writer_errors, copy_buf_size,
            ),
            name="merge-writer",
            daemon=True,
        )
        writer_thread.start()

        def _on_future_done(fut: Future[int], tmp: Path, zp: Path) -> None:
            """Callback fired when a worker completes — enqueues for writer."""
            try:
                bw = fut.result()
            except Exception:
                bw = 0
            write_q.put((tmp, zp, bw))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            for i, zp in enumerate(zip_files):
                # Graduated backpressure based on memory usage
                if monitor is not None and hasattr(monitor, "memory_pct"):
                    bp_soft, bp_warn, bp_crit = backpressure_thresholds
                    bp_soft_sleep, bp_warn_sleep = backpressure_sleeps
                    pct = monitor.memory_pct()
                    if pct >= bp_crit:
                        monitor.wait_for_memory(timeout=120)
                    elif pct >= bp_warn:
                        time.sleep(bp_warn_sleep)
                    elif pct >= bp_soft:
                        time.sleep(bp_soft_sleep)

                # Bound concurrency via semaphore
                sem.acquire()

                # Check for writer thread errors
                if writer_errors:
                    raise writer_errors[0]

                tmp_path = tmp_dir / f"{i:06d}.tmp"
                # Build per-ZIP skip set from validation manifest
                zip_skip_entries: frozenset[str] = frozenset()
                if manifest is not None:
                    zip_report = manifest.get(zp.name)
                    if zip_report is not None:
                        zip_skip_entries = frozenset(
                            e.entry_name
                            for e in zip_report.invalid_entries
                        )
                future = pool.submit(
                    _extract_zip_to_file, zp, tmp_path, bulk_read_size,
                    zip_skip_entries,
                )
                future.add_done_callback(
                    lambda fut, t=tmp_path, z=zp: _on_future_done(fut, t, z)
                )

        # Signal writer to finish and wait
        write_q.put(None)
        writer_thread.join(timeout=writer_join_timeout)

    if writer_errors:
        raise writer_errors[0]

    # Deactivate fast monitoring
    if monitor is not None and hasattr(monitor, "set_active"):
        monitor.set_active(False)

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
