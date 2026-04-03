"""Pipeline state tracking, result dataclasses, and logging setup."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

from .constants import DEFAULT_LOG_BACKUP_COUNT, DEFAULT_LOG_MAX_BYTES, LOG_FILENAME

if TYPE_CHECKING:
    from .telemetry import TelemetryRecorder

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class MergeResult:
    """Outcome of a merge operation."""

    chunk_files: list[Path] = field(default_factory=list)
    total_zips: int = 0
    processed_zips: list[str] = field(default_factory=list)
    failed_zips: list[str] = field(default_factory=list)
    total_bytes: int = 0
    skipped_entries: int = 0

    @property
    def error_rate(self) -> float:
        if self.total_zips == 0:
            return 0.0
        return len(self.failed_zips) / self.total_zips


@dataclass
class ValidateResult:
    """Outcome of a standalone validation operation."""

    total_zips: int = 0
    total_entries: int = 0
    valid_entries: int = 0
    invalid_entries: int = 0
    checksum_ok: int = 0
    checksum_failed: list[str] = field(default_factory=list)
    checksum_missing: int = 0


@dataclass
class ExportResult:
    """Outcome of an export-all operation."""

    succeeded: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    parquet_files: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline state persistence
# ---------------------------------------------------------------------------

_STATE_VERSION = 1


@dataclass
class StageState:
    """State of a single pipeline stage."""

    status: str = "pending"  # pending | running | complete | failed
    completed_at: str | None = None
    error: str | None = None
    # Merge-specific
    processed_zips: list[str] = field(default_factory=list)
    failed_zips: list[str] = field(default_factory=list)
    chunks_written: int = 0
    # Export-specific
    completed_queries: list[str] = field(default_factory=list)
    failed_queries: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict = {"status": self.status}
        if self.completed_at:
            d["completed_at"] = self.completed_at
        if self.error:
            d["error"] = self.error
        if self.processed_zips:
            d["processed_zips"] = self.processed_zips
        if self.failed_zips:
            d["failed_zips"] = self.failed_zips
        if self.chunks_written:
            d["chunks_written"] = self.chunks_written
        if self.completed_queries:
            d["completed_queries"] = self.completed_queries
        if self.failed_queries:
            d["failed_queries"] = self.failed_queries
        return d

    @classmethod
    def from_dict(cls, d: dict) -> StageState:
        return cls(
            status=d.get("status", "pending"),
            completed_at=d.get("completed_at"),
            error=d.get("error"),
            processed_zips=d.get("processed_zips", []),
            failed_zips=d.get("failed_zips", []),
            chunks_written=d.get("chunks_written", 0),
            completed_queries=d.get("completed_queries", []),
            failed_queries=d.get("failed_queries", {}),
        )


@dataclass
class PipelineState:
    """Tracks progress across pipeline stages for checkpoint/resume."""

    started_at: str = ""
    updated_at: str = ""
    stages: dict[str, StageState] = field(default_factory=dict)
    _telemetry: TelemetryRecorder | None = field(default=None, repr=False, compare=False)

    def set_telemetry(self, telemetry: TelemetryRecorder) -> None:
        """Attach a telemetry recorder for stage event emission."""
        self._telemetry = telemetry

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def is_complete(self, stage: str) -> bool:
        return self.stages.get(stage, StageState()).status == "complete"

    def mark_running(self, stage: str) -> None:
        s = self.stages.setdefault(stage, StageState())
        s.status = "running"
        self.updated_at = self._now()
        if self._telemetry:
            self._telemetry.emit("stage_start", {"stage": stage})

    def mark_complete(self, stage: str) -> None:
        s = self.stages.setdefault(stage, StageState())
        s.status = "complete"
        s.completed_at = self._now()
        s.error = None
        self.updated_at = self._now()
        if self._telemetry:
            self._telemetry.emit("stage_end", {
                "stage": stage,
                "status": "complete",
            })

    def mark_failed(self, stage: str, error: str) -> None:
        s = self.stages.setdefault(stage, StageState())
        s.status = "failed"
        s.error = error
        self.updated_at = self._now()
        if self._telemetry:
            self._telemetry.emit("stage_end", {
                "stage": stage,
                "status": "failed",
                "error": error,
            })

    def get_stage(self, stage: str) -> StageState:
        return self.stages.setdefault(stage, StageState())

    def update_merge(self, result: MergeResult) -> None:
        s = self.get_stage("merge")
        s.processed_zips = result.processed_zips
        s.failed_zips = result.failed_zips
        s.chunks_written = len(result.chunk_files)
        if result.failed_zips:
            s.status = "complete"  # complete with warnings
        else:
            s.status = "complete"
        s.completed_at = self._now()
        self.updated_at = self._now()

    def update_export(self, result: ExportResult) -> None:
        s = self.get_stage("export")
        s.completed_queries = result.succeeded
        s.failed_queries = result.failed
        if result.failed:
            s.status = "failed" if not result.succeeded else "complete"
        else:
            s.status = "complete"
        s.completed_at = self._now()
        self.updated_at = self._now()

    # -- Serialization --

    def to_dict(self) -> dict:
        return {
            "version": _STATE_VERSION,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> PipelineState:
        return cls(
            started_at=d.get("started_at", ""),
            updated_at=d.get("updated_at", ""),
            stages={
                k: StageState.from_dict(v)
                for k, v in d.get("stages", {}).items()
            },
        )

    def save(self, path: Path) -> None:
        """Atomically write state to *path*."""
        data = json.dumps(self.to_dict(), indent=2)
        # Write to temp file in the same directory, then atomically rename
        fd, tmp = tempfile.mkstemp(
            dir=path.parent, prefix=".state_", suffix=".tmp"
        )
        try:
            os.write(fd, data.encode())
            os.close(fd)
            os.replace(tmp, path)
        except BaseException:
            os.close(fd) if not os.get_inheritable(fd) else None
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    @classmethod
    def load(cls, path: Path) -> PipelineState:
        """Load state from *path*, returning fresh state if missing/corrupt."""
        try:
            d = json.loads(path.read_text())
            return cls.from_dict(d)
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return cls()

    @classmethod
    def fresh(cls) -> PipelineState:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return cls(started_at=now, updated_at=now)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def setup_logging(
    work_dir: Path,
    level: int = logging.INFO,
    max_bytes: int = DEFAULT_LOG_MAX_BYTES,
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
) -> logging.Logger:
    """Configure rotating file logging for the pipeline.

    Returns the root ``europeana_qlever`` logger.  All modules should use
    ``logging.getLogger(__name__)`` to obtain child loggers.

    Idempotent — safe to call multiple times.
    """
    logger = logging.getLogger("europeana_qlever")

    # Avoid adding duplicate handlers on repeated calls
    if any(
        isinstance(h, RotatingFileHandler) for h in logger.handlers
    ):
        return logger

    logger.setLevel(level)

    work_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        work_dir / LOG_FILENAME,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s  %(message)s")
    )
    logger.addHandler(handler)

    return logger
