"""Validate Europeana TTL ZIPs: checksum verification and rdflib-based parsing.

Core validation functions used by both the standalone ``validate`` command
(read-only pre-flight check) and the ``merge`` command (inline validation
during extraction). The merge worker imports :func:`validate_entry` and
:func:`verify_one_checksum` to validate each TTL entry before writing.

The standalone ``validate`` command uses :func:`validate_all` to scan all
ZIPs and print a summary report without writing any files.

.. note:: **Europeana FTP md5sum files are unreliable** (as of March 2026).

   Of ~2,300 md5sum files tested, only 7% match their companion ZIPs.
   Two issues exist on the server: (1) stale checksums — md5sum files are
   periodically regenerated from freshly built ZIPs that are never published
   to the FTP, while the actual ZIP files retain older content; (2) leading-
   zero stripping — 126 md5sum files contain 31 or 30 hex characters instead
   of the expected 32.  Checksum verification is therefore **skipped by
   default** in the merge pipeline (``--checksum-policy=skip``).
"""

from __future__ import annotations

import hashlib
import logging
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
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
from .state import ValidateResult

logger = logging.getLogger(__name__)

# Buffer size for MD5 hashing (8 MB)
_CHECKSUM_BUF_SIZE = 8_388_608

# Suppress rdflib warnings during bulk validation
_RDFLIB_LOGGERS = ("rdflib.term", "rdflib.plugins.parsers.notation3")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class EntryIssue:
    """A single invalid TTL entry within a ZIP."""

    entry_name: str
    error: str


@dataclass
class ZipReport:
    """Validation result for an entire ZIP file."""

    zip_name: str
    checksum_ok: bool | None = None  # None = no .md5sum file found
    checksum_error: str | None = None
    invalid_entries: list[EntryIssue] = field(default_factory=list)
    total_entries: int = 0
    valid_count: int = 0
    invalid_count: int = 0


# ---------------------------------------------------------------------------
# Checksum verification
# ---------------------------------------------------------------------------


def _find_checksum_file(zip_path: Path) -> Path | None:
    """Locate a companion MD5 checksum file for *zip_path*.

    Checks ``<name>.zip.md5sum``, ``<name>.md5sum``, and ``<name>.zip.md5``.
    """
    candidates = [
        zip_path.with_suffix(".zip.md5sum"),
        zip_path.with_name(zip_path.name + ".md5sum"),
        zip_path.with_suffix(".zip.md5"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _parse_md5sum_file(path: Path) -> str:
    """Extract the hex MD5 hash from a checksum file."""
    text = path.read_text().strip()
    return text.split()[0].lower()


def _compute_md5(path: Path) -> str:
    """Compute MD5 hex digest of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(_CHECKSUM_BUF_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def verify_one_checksum(zip_path: Path) -> tuple[str, bool | None, str | None]:
    """Verify a single ZIP's checksum. Returns (zip_name, ok, error_msg).

    Returns ``(name, None, None)`` if no checksum file exists.
    """
    cs_file = _find_checksum_file(zip_path)
    if cs_file is None:
        return (zip_path.name, None, None)
    try:
        expected = _parse_md5sum_file(cs_file)
        actual = _compute_md5(zip_path)
        if expected == actual:
            return (zip_path.name, True, None)
        return (
            zip_path.name,
            False,
            f"expected {expected}, got {actual}",
        )
    except Exception as exc:
        return (zip_path.name, False, str(exc))


def verify_checksums(
    zip_files: list[Path],
    workers: int = 4,
    progress_cb: callable | None = None,
) -> tuple[list[str], list[tuple[str, str]], list[str]]:
    """Verify MD5 checksums for all ZIPs against companion .md5sum files.

    Returns (ok_names, failed: [(name, error)], missing_names).
    """
    ok: list[str] = []
    failed: list[tuple[str, str]] = []
    missing: list[str] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(verify_one_checksum, zp): zp for zp in zip_files
        }
        for fut in as_completed(futures):
            name, result, error = fut.result()
            if result is None:
                missing.append(name)
            elif result:
                ok.append(name)
            else:
                failed.append((name, error or "unknown error"))
            if progress_cb is not None:
                progress_cb()

    return ok, failed, missing


# ---------------------------------------------------------------------------
# TTL entry validation
# ---------------------------------------------------------------------------


def validate_entry(entry_name: str, data: bytes) -> EntryIssue | None:
    """Parse a single TTL entry with rdflib. Returns None if valid.

    If rdflib raises any exception during parsing, returns an
    :class:`EntryIssue` with the error message.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return EntryIssue(entry_name=entry_name, error=f"UTF-8 decode error: {exc}")

    try:
        g = rdflib.Graph()
        for logger_name in _RDFLIB_LOGGERS:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        g.parse(data=text, format="turtle")
        del g
        return None
    except Exception as exc:
        return EntryIssue(entry_name=entry_name, error=str(exc))


# ---------------------------------------------------------------------------
# Per-ZIP validation (for standalone validate command)
# ---------------------------------------------------------------------------


def _validate_zip(zip_path: Path) -> ZipReport:
    """Open a ZIP and validate each .ttl entry with rdflib."""
    zip_name = zip_path.name
    issues: list[EntryIssue] = []
    total = 0
    valid = 0

    try:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if not name.endswith(".ttl"):
                    continue
                total += 1
                try:
                    data = zf.read(name)
                except Exception as exc:
                    issues.append(
                        EntryIssue(entry_name=name, error=f"ZIP read error: {exc}")
                    )
                    continue

                issue = validate_entry(name, data)
                if issue is None:
                    valid += 1
                else:
                    issues.append(issue)
    except (zipfile.BadZipFile, OSError) as exc:
        return ZipReport(
            zip_name=zip_name,
            invalid_entries=[
                EntryIssue(entry_name="<archive>", error=f"Cannot open ZIP: {exc}")
            ],
            total_entries=0,
            valid_count=0,
            invalid_count=1,
        )

    return ZipReport(
        zip_name=zip_name,
        invalid_entries=issues,
        total_entries=total,
        valid_count=valid,
        invalid_count=len(issues),
    )


# ---------------------------------------------------------------------------
# Standalone validate orchestrator (read-only, no manifest)
# ---------------------------------------------------------------------------


def validate_all(
    ttl_dir: Path,
    *,
    workers: int = 4,
    verify_checksums_flag: bool = True,
) -> ValidateResult:
    """Run full validation: checksums first, then rdflib TTL parsing.

    This is the read-only pre-flight check used by the standalone
    ``validate`` CLI command. It does not write any files — just reports.
    """
    zip_files = sorted(ttl_dir.glob("*.zip"))

    if not zip_files:
        display.console.print(f"[red]No ZIP files found in {ttl_dir}[/red]")
        return ValidateResult()

    # Step 1: Checksum verification
    checksum_ok_names: list[str] = []
    checksum_failed: list[tuple[str, str]] = []
    checksum_missing: list[str] = []
    checksum_failed_set: set[str] = set()

    if verify_checksums_flag:
        display.console.print(
            f"[bold]Step 1/2 · Verifying checksums for "
            f"{len(zip_files):,} ZIPs…[/bold]"
        )
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=display.console,
        ) as progress:
            task = progress.add_task("Checksums", total=len(zip_files))

            def _cs_cb() -> None:
                progress.advance(task)

            checksum_ok_names, checksum_failed, checksum_missing = verify_checksums(
                zip_files, workers=workers, progress_cb=_cs_cb,
            )

        checksum_failed_set = {name for name, _ in checksum_failed}

        if checksum_failed:
            display.console.print(
                f"[red]{len(checksum_failed)} checksum failure(s)[/red]"
            )
            for name, err in checksum_failed[:10]:
                display.console.print(f"  [red]{name}[/red]: {err}")
            if len(checksum_failed) > 10:
                display.console.print(
                    f"  … and {len(checksum_failed) - 10} more"
                )
        else:
            display.console.print("[green]All checksums OK[/green]")

        if checksum_missing:
            display.console.print(
                f"[dim]{len(checksum_missing):,} ZIP(s) have no checksum file[/dim]"
            )
    else:
        display.console.print("[dim]Checksum verification skipped[/dim]")
        checksum_missing = [zp.name for zp in zip_files]

    zips_to_validate = [
        zp for zp in zip_files if zp.name not in checksum_failed_set
    ]

    # Step 2: TTL validation
    display.console.print(
        f"[bold]Step 2/2 · Validating TTL in "
        f"{len(zips_to_validate):,} ZIPs ({workers} workers)…[/bold]"
    )

    reports: list[ZipReport] = []

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
        task = progress.add_task("Validating", total=len(zips_to_validate))

        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_validate_zip, zp): zp for zp in zips_to_validate
            }
            for fut in as_completed(futures):
                report = fut.result()
                if report.zip_name in set(checksum_ok_names):
                    report.checksum_ok = True
                elif report.zip_name in set(checksum_missing):
                    report.checksum_ok = None
                reports.append(report)
                progress.advance(task)

    total_entries = sum(r.total_entries for r in reports)
    valid_entries = sum(r.valid_count for r in reports)
    invalid_entries = sum(r.invalid_count for r in reports)

    # Summary
    display.console.print(
        f"\n[green]Validation complete.[/green]\n"
        f"  {valid_entries:,} valid entries\n"
        f"  {invalid_entries:,} invalid entries"
    )
    if checksum_failed:
        display.console.print(
            f"  {len(checksum_failed)} checksum failure(s)"
        )

    for r in reports:
        for issue in r.invalid_entries:
            logger.warning(
                "Invalid TTL entry: %s/%s — %s",
                r.zip_name, issue.entry_name, issue.error,
            )

    return ValidateResult(
        total_zips=len(zip_files),
        total_entries=total_entries,
        valid_entries=valid_entries,
        invalid_entries=invalid_entries,
        checksum_ok=len(checksum_ok_names),
        checksum_failed=[name for name, _ in checksum_failed],
        checksum_missing=len(checksum_missing),
    )
