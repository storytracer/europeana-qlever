"""Merge Europeana per-record TTL ZIPs into chunked, QLever-ready TTL files.

Strategy
--------
1. **scan_prefixes** — Sample a subset of ZIPs and use rdflib to parse
   individual TTL files, collecting every @prefix declaration. This catches
   provider-specific prefixes not in the canonical EDM set.
2. **merge** — Process all ZIPs in parallel (ProcessPoolExecutor, CPU-bound
   due to rdflib validation). Each worker reads TTL entries, validates them
   with rdflib, strips prefix/base declarations, and writes valid content
   to a temp file. Invalid entries are skipped and logged.
   A dedicated writer thread assembles temp files into chunked output
   files, each prepended with the master prefix block.

Memory efficiency: workers write to temp files, the writer reads temp files
in 8 MB chunks. A semaphore bounds concurrent in-flight work, and an
optional ResourceMonitor provides graduated backpressure when system
memory is under pressure.
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
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
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
from .constants import DEFAULT_COPY_BUF_SIZE, EDM_PREFIXES
from .state import MergeResult
from .validate import validate_entry, verify_one_checksum

logger = logging.getLogger(__name__)

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
# Single-ZIP extraction with inline rdflib validation
# ---------------------------------------------------------------------------

def _extract_zip_to_file(
    zip_path: Path,
    output_file: Path,
    checksum_policy: str = "skip",
) -> tuple[int, int, str | None]:
    """Extract validated TTL from *zip_path*, skipping invalid entries.

    Each ``.ttl`` entry is read into memory, parsed with rdflib to validate
    Turtle syntax, and only written if parsing succeeds. Invalid entries are
    logged and skipped.

    Returns ``(bytes_written, invalid_count, failure_reason)`` where
    *failure_reason* is ``None`` on success, ``"checksum"`` when a checksum
    mismatch caused the ZIP to be skipped, or ``"extraction"`` on error.
    """
    try:
        # Verify checksum if requested
        if checksum_policy != "skip":
            _name, cs_ok, cs_err = verify_one_checksum(zip_path)
            if cs_ok is False:
                if checksum_policy == "strict":
                    logger.warning(
                        "Checksum mismatch for %s: %s — skipping ZIP",
                        zip_path.name, cs_err,
                    )
                    return (0, 0, "checksum")
                # policy == "warn": log but continue
                logger.warning(
                    "Checksum mismatch for %s: %s — continuing anyway",
                    zip_path.name, cs_err,
                )

        bytes_written = 0
        invalid_count = 0

        with open(output_file, "wb") as out:
            with zipfile.ZipFile(zip_path) as zf:
                for name in zf.namelist():
                    if not name.endswith(".ttl"):
                        continue

                    try:
                        data = zf.read(name)
                    except Exception as exc:
                        invalid_count += 1
                        logger.warning(
                            "Cannot read %s/%s: %s", zip_path.name, name, exc,
                        )
                        continue

                    # Validate with rdflib
                    issue = validate_entry(name, data)
                    if issue is not None:
                        invalid_count += 1
                        logger.warning(
                            "Invalid TTL %s/%s: %s",
                            zip_path.name, name, issue.error,
                        )
                        continue

                    # Strip prefix/base headers and write
                    for raw_line in data.split(b"\n"):
                        line = raw_line.decode("utf-8", errors="replace")
                        if not line.strip():
                            continue
                        if _PREFIX_RE.match(line):
                            continue
                        out.write(raw_line + b"\n")
                        bytes_written += len(raw_line) + 1

        return (bytes_written, invalid_count, None)

    except Exception as exc:
        logger.error("Extraction failed for %s: %s", zip_path.name, exc)
        try:
            output_file.unlink(missing_ok=True)
        except OSError:
            pass
        return (0, 0, "extraction")


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
    checksum_failed_zips: list[str],
    skipped_entries_total: list[int],
    sem: object,  # AdaptiveThrottle or threading.Semaphore (duck-typed)
    progress_cb: callable | None,
    dashboard: object | None,
    error_holder: list,
    copy_buf_size: int = DEFAULT_COPY_BUF_SIZE,
) -> None:
    """Background writer that assembles temp files into chunk output files.

    Reads ``(tmp_path, zip_path, bytes_written, invalid_count, reason)``
    tuples from *write_q*. A ``None`` sentinel signals shutdown.
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
            tmp_path, zip_path, bytes_written, invalid_count, reason = item

            skipped_entries_total[0] += invalid_count

            if bytes_written > 0 and tmp_path.exists():
                with open(tmp_path, "rb") as src:
                    shutil.copyfileobj(src, fh, length=copy_buf_size)
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
                    if reason == "checksum":
                        checksum_failed_zips.append(zip_path.name)
                        logger.warning("Checksum mismatch — skipped: %s", zip_path.name)
                    else:
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
    dashboard: object | None = None,
    copy_buf_size: int = DEFAULT_COPY_BUF_SIZE,
    backpressure_thresholds: tuple[float, float, float] = (70.0, 80.0, 90.0),
    backpressure_sleeps: tuple[float, float] = (0.1, 0.5),
    cpu_target: float = 85.0,
    cpu_low: float = 65.0,
    throttle_consecutive_samples: int = 3,
    writer_join_timeout: int = 300,
    checksum_policy: str = "skip",
) -> MergeResult:
    """Merge all TTL ZIPs into chunked output files with parallel extraction.

    Each TTL entry is validated with rdflib before writing. Invalid entries
    are skipped and logged. Checksum verification is controlled by
    *checksum_policy*: ``"skip"`` (default, no verification), ``"warn"``
    (log mismatches but continue), or ``"strict"`` (skip mismatched ZIPs).

    Uses ProcessPoolExecutor for true parallelism (rdflib parsing is
    CPU-bound and would be serialised by the GIL with threads).

    Parameters
    ----------
    ttl_dir : Path
        Directory containing Europeana .zip files.
    output_dir : Path
        Where to write the merged ``europeana_NNNN.ttl`` chunk files.
    chunk_size_gb : float
        Approximate maximum size of each output chunk in gigabytes.
    workers : int
        Number of parallel processes for ZIP extraction + validation.
    prefixes : dict or None
        Prefix map to use. If ``None``, runs ``scan_prefixes_from_sample``
        automatically.
    monitor : ResourceMonitor or None
        Optional resource monitor for memory backpressure. When provided
        and memory is high, submissions are throttled or paused.
    skip_zips : frozenset[str]
        ZIP filenames to skip (for resuming a previous merge).
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

    # Adaptive throttle replaces fixed semaphore — dynamically adjusts
    # permits based on CPU and memory pressure via monitor snapshots.
    from .throttle import AdaptiveThrottle

    bp_soft, _bp_warn, bp_crit = backpressure_thresholds

    def _on_throttle_adjust(current: int, maximum: int, reason: str) -> None:
        if dashboard is not None:
            try:
                dashboard.set_info("concurrency", f"{current}/{maximum} ({reason})")
            except Exception:
                pass

    initial_concurrency = max(4, workers // 2)
    sem = AdaptiveThrottle(
        initial_permits=initial_concurrency,
        max_permits=workers,
        min_permits=2,
        cpu_target=cpu_target,
        cpu_low=cpu_low,
        memory_target=bp_crit,
        memory_low=bp_soft,
        consecutive_samples=throttle_consecutive_samples,
        step_down=2,
        step_up=2,
        on_adjust=_on_throttle_adjust,
    )
    if dashboard is not None:
        dashboard.set_info("concurrency", f"{initial_concurrency}/{workers}")

    # Shared state (written only by writer thread)
    processed_zips: list[str] = list(skip_zips)
    failed_zips: list[str] = []
    checksum_failed_zips: list[str] = []
    skipped_entries_total: list[int] = [0]  # mutable container for writer thread

    # Writer queue + thread
    write_q: queue.Queue = queue.Queue(maxsize=max(4, workers * 2))
    writer_errors: list[Exception] = []

    # Activate faster monitoring during merge and wire adaptive throttle
    if monitor is not None and hasattr(monitor, "set_active"):
        monitor.set_active(True)
        existing_cb = monitor._on_sample

        def _chained_sample(snap: object) -> None:
            sem.adjust(snap)
            if existing_cb is not None:
                existing_cb(snap)

        monitor._on_sample = _chained_sample

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
                chunk_files, processed_zips, failed_zips, checksum_failed_zips,
                skipped_entries_total,
                sem, _progress_cb, dashboard, writer_errors, copy_buf_size,
            ),
            name="merge-writer",
            daemon=True,
        )
        writer_thread.start()

        def _on_future_done(fut: Future, tmp: Path, zp: Path) -> None:
            """Callback fired when a worker completes — enqueues for writer."""
            try:
                bw, inv, reason = fut.result()
            except Exception as exc:
                logger.error("Worker process failed for %s: %s", zp.name, exc)
                bw, inv, reason = 0, 0, "extraction"
            write_q.put((tmp, zp, bw, inv, reason))

        interrupted = False
        try:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                for i, zp in enumerate(zip_files):
                    # Adaptive throttle bounds concurrency — blocks when
                    # permits are exhausted (auto-adjusted by CPU/memory)
                    sem.acquire()

                    # Check for writer thread errors
                    if writer_errors:
                        raise writer_errors[0]

                    tmp_path = tmp_dir / f"{i:06d}.tmp"
                    future = pool.submit(
                        _extract_zip_to_file, zp, tmp_path, checksum_policy,
                    )
                    future.add_done_callback(
                        lambda fut, t=tmp_path, z=zp: _on_future_done(fut, t, z)
                    )
        except KeyboardInterrupt:
            interrupted = True
            logger.info("Merge interrupted by user after %d/%d ZIPs",
                        len(processed_zips), len(zip_files))
        finally:
            # Always signal writer to finish and wait, even on interrupt
            write_q.put(None)
            writer_thread.join(timeout=10 if interrupted else writer_join_timeout)

    if not interrupted and writer_errors:
        raise writer_errors[0]

    # Deactivate fast monitoring
    if monitor is not None and hasattr(monitor, "set_active"):
        monitor.set_active(False)

    # Clean up temp directory
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # Summary
    total_bytes = sum(p.stat().st_size for p in chunk_files)
    if interrupted:
        display.console.print(
            f"\n[yellow]Interrupted.[/yellow] {len(processed_zips):,}/{len(zip_files):,} "
            f"ZIPs processed → {len(chunk_files)} chunk(s) "
            f"({total_bytes / 1e9:.1f} GB)"
        )
    else:
        display.console.print(
            f"\n[green]Done.[/green] {len(zip_files):,} ZIPs → "
            f"{len(chunk_files)} chunk(s) "
            f"({total_bytes / 1e9:.1f} GB) in {display.short_path(output_dir)}"
        )
        for p in chunk_files:
            display.console.print(f"  {p.name}  ({p.stat().st_size / 1e9:.2f} GB)")

    if checksum_failed_zips:
        display.console.print(
            f"\n[yellow]{len(checksum_failed_zips):,} ZIP(s) skipped: "
            f"MD5 checksum mismatch[/yellow]"
        )
        logger.warning(
            "Merge: %d ZIPs skipped due to checksum mismatch",
            len(checksum_failed_zips),
        )

    if failed_zips:
        display.console.print(
            f"\n[yellow]{len(failed_zips):,} ZIP(s) failed: "
            f"extraction error[/yellow]"
        )
        logger.warning(
            "Merge completed with %d failed ZIPs out of %d",
            len(failed_zips), len(zip_files),
        )

    total_skipped = skipped_entries_total[0]
    if total_skipped:
        display.console.print(
            f"[yellow]{total_skipped:,} invalid TTL entries skipped[/yellow]"
        )

    result = MergeResult(
        chunk_files=chunk_files,
        total_zips=len(all_zips),
        processed_zips=processed_zips,
        failed_zips=failed_zips,
        total_bytes=total_bytes,
        skipped_entries=total_skipped,
    )
    logger.info(
        "Merge %s: %d chunks, %d processed, %d failed, "
        "%d checksum-skipped, %d skipped entries, %.1f GB",
        "interrupted" if interrupted else "complete",
        len(chunk_files), len(processed_zips), len(failed_zips),
        len(checksum_failed_zips), total_skipped, total_bytes / 1e9,
    )
    if interrupted:
        raise KeyboardInterrupt
    return result
