"""Validate Europeana TTL ZIPs: checksum verification and rdflib-based parsing.

The validation stage runs **before** merge in the pipeline. It:

1. Verifies MD5 checksums of all ZIP files against companion ``.md5sum`` files
   to ensure download integrity.
2. Parses every TTL entry inside each ZIP with rdflib to catch *any* Turtle
   syntax error. Invalid entries are logged and excluded from the merge via a
   persisted manifest file.

CPU-bound rdflib parsing is parallelised with :class:`ProcessPoolExecutor`
to avoid GIL bottlenecks. Checksum verification uses
:class:`ThreadPoolExecutor` (I/O-bound).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
from .constants import VALIDATE_MANIFEST
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

    def to_dict(self) -> dict:
        return {"entry_name": self.entry_name, "error": self.error}

    @classmethod
    def from_dict(cls, d: dict) -> EntryIssue:
        return cls(entry_name=d["entry_name"], error=d["error"])


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

    def to_dict(self) -> dict:
        d: dict = {"zip_name": self.zip_name}
        if self.checksum_ok is not None:
            d["checksum_ok"] = self.checksum_ok
        if self.checksum_error:
            d["checksum_error"] = self.checksum_error
        if self.invalid_entries:
            d["invalid_entries"] = [e.to_dict() for e in self.invalid_entries]
        d["total_entries"] = self.total_entries
        d["valid_count"] = self.valid_count
        d["invalid_count"] = self.invalid_count
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ZipReport:
        return cls(
            zip_name=d["zip_name"],
            checksum_ok=d.get("checksum_ok"),
            checksum_error=d.get("checksum_error"),
            invalid_entries=[
                EntryIssue.from_dict(e) for e in d.get("invalid_entries", [])
            ],
            total_entries=d.get("total_entries", 0),
            valid_count=d.get("valid_count", 0),
            invalid_count=d.get("invalid_count", 0),
        )


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
    """Extract the hex MD5 hash from a checksum file.

    Supports formats:
    - ``<hash>  <filename>``
    - ``<hash> *<filename>``
    - bare ``<hash>``
    """
    text = path.read_text().strip()
    # Take the first whitespace-delimited token
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


def _verify_one_checksum(zip_path: Path) -> tuple[str, bool | None, str | None]:
    """Verify a single ZIP's checksum. Returns (zip_name, ok, error_msg)."""
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

    Uses ThreadPoolExecutor (I/O-bound).

    Returns
    -------
    ok : list[str]
        ZIP filenames whose checksums matched.
    failed : list[tuple[str, str]]
        (zip_name, error_message) for checksum mismatches.
    missing : list[str]
        ZIP filenames with no companion checksum file.
    """
    ok: list[str] = []
    failed: list[tuple[str, str]] = []
    missing: list[str] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_verify_one_checksum, zp): zp for zp in zip_files
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
# TTL entry validation (runs in worker process)
# ---------------------------------------------------------------------------


def _validate_entry(entry_name: str, data: bytes) -> EntryIssue | None:
    """Parse a single TTL entry with rdflib. Returns None if valid.

    If rdflib raises any exception during parsing, returns an
    :class:`EntryIssue` with the error message. The entry will be skipped
    during merge.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return EntryIssue(entry_name=entry_name, error=f"UTF-8 decode error: {exc}")

    try:
        g = rdflib.Graph()
        # Suppress noisy rdflib warnings (e.g. malformed xsd:hexBinary)
        for logger_name in _RDFLIB_LOGGERS:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        g.parse(data=text, format="turtle")
        del g
        return None
    except Exception as exc:
        return EntryIssue(entry_name=entry_name, error=str(exc))


# ---------------------------------------------------------------------------
# Per-ZIP validation (runs in worker process)
# ---------------------------------------------------------------------------


def _validate_zip(zip_path: Path) -> ZipReport:
    """Open a ZIP and validate each .ttl entry with rdflib.

    Called by ProcessPoolExecutor — must be picklable (top-level function
    with Path argument).
    """
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

                issue = _validate_entry(name, data)
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
# Manifest I/O
# ---------------------------------------------------------------------------


def save_manifest(reports: list[ZipReport], path: Path) -> None:
    """Atomically write the validation manifest.

    Only ZIPs with invalid entries or checksum failures are stored.
    Valid-only ZIPs are implicitly valid (absent from manifest).
    """
    manifest: dict = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "zips": {},
    }
    for r in reports:
        if r.invalid_entries or r.checksum_ok is False:
            manifest["zips"][r.zip_name] = r.to_dict()

    data = json.dumps(manifest, indent=2).encode()
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".manifest_", suffix=".tmp")
    try:
        os.write(fd, data)
        os.close(fd)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_manifest(path: Path) -> dict[str, ZipReport]:
    """Load a validation manifest, returning {zip_name: ZipReport}.

    Returns an empty dict if the file is missing or corrupt.
    """
    try:
        raw = json.loads(path.read_text())
        return {
            name: ZipReport.from_dict(d)
            for name, d in raw.get("zips", {}).items()
        }
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {}


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def validate_all(
    ttl_dir: Path,
    output_dir: Path,
    *,
    workers: int = 4,
    verify_checksums_flag: bool = True,
    dashboard: object | None = None,
) -> ValidateResult:
    """Run full validation: checksums first, then rdflib TTL parsing.

    Parameters
    ----------
    ttl_dir : Path
        Directory containing Europeana .zip files.
    output_dir : Path
        Where to write the validation manifest.
    workers : int
        Parallel workers for both checksum (threads) and TTL (processes).
    verify_checksums_flag : bool
        Whether to verify MD5 checksums.
    dashboard : Dashboard or None
        Optional dashboard for live progress updates.

    Returns
    -------
    ValidateResult
        Summary of validation outcomes.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_files = sorted(ttl_dir.glob("*.zip"))

    if not zip_files:
        display.console.print(f"[red]No ZIP files found in {ttl_dir}[/red]")
        return ValidateResult()

    # ------------------------------------------------------------------
    # Step 1: Checksum verification (all ZIPs, upfront)
    # ------------------------------------------------------------------
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

    # Filter out checksum-failed ZIPs before TTL validation
    zips_to_validate = [
        zp for zp in zip_files if zp.name not in checksum_failed_set
    ]

    # ------------------------------------------------------------------
    # Step 2: TTL validation (ProcessPoolExecutor, CPU-bound)
    # ------------------------------------------------------------------
    display.console.print(
        f"[bold]Step 2/2 · Validating TTL in "
        f"{len(zips_to_validate):,} ZIPs ({workers} workers)…[/bold]"
    )

    reports: list[ZipReport] = []

    # Pre-populate reports for checksum-failed ZIPs
    for name, err in checksum_failed:
        reports.append(
            ZipReport(
                zip_name=name,
                checksum_ok=False,
                checksum_error=err,
                invalid_entries=[
                    EntryIssue(
                        entry_name="<archive>",
                        error=f"Skipped: checksum failure ({err})",
                    )
                ],
                total_entries=0,
                valid_count=0,
                invalid_count=0,
            )
        )

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
                # Attach checksum info
                if report.zip_name in {n for n in checksum_ok_names}:
                    report.checksum_ok = True
                elif report.zip_name in {n for n in checksum_missing}:
                    report.checksum_ok = None
                reports.append(report)
                progress.advance(task)

                if dashboard is not None:
                    try:
                        dashboard.advance()
                    except Exception:
                        pass

    # ------------------------------------------------------------------
    # Save manifest and build result
    # ------------------------------------------------------------------
    manifest_path = output_dir / VALIDATE_MANIFEST
    save_manifest(reports, manifest_path)

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
            f"  {len(checksum_failed)} checksum failure(s) "
            f"(ZIPs excluded from merge)"
        )

    # Log individual invalid entries
    for r in reports:
        for issue in r.invalid_entries:
            logger.warning(
                "Invalid TTL entry: %s/%s — %s",
                r.zip_name, issue.entry_name, issue.error,
            )

    result = ValidateResult(
        total_zips=len(zip_files),
        total_entries=total_entries,
        valid_entries=valid_entries,
        invalid_entries=invalid_entries,
        checksum_ok=len(checksum_ok_names),
        checksum_failed=[name for name, _ in checksum_failed],
        checksum_missing=len(checksum_missing),
        manifest_path=manifest_path,
    )
    logger.info(
        "Validation complete: %d ZIPs, %d entries (%d valid, %d invalid), "
        "%d checksum OK, %d failed, %d missing",
        result.total_zips, result.total_entries,
        result.valid_entries, result.invalid_entries,
        result.checksum_ok, len(result.checksum_failed),
        result.checksum_missing,
    )
    return result
