"""Unified structured telemetry: JSONL event stream and per-command profiling.

Replaces fragmented logging/monitoring with a single machine-readable event
stream.  Every event is a JSON object written to ``<work-dir>/telemetry.jsonl``.

Usage::

    recorder = TelemetryRecorder(path, command="export")
    recorder.emit("export_start", {"name": "items_core"})
    recorder.close()

Per-command profiling is handled by :func:`command_span`::

    with command_span(telemetry, {"arg": "val"}) as counters:
        counters["rows"] = 42
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import psutil

from . import display


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_rss_mb() -> float:
    """Return current process RSS in MB."""
    return psutil.Process().memory_info().rss / (1024 * 1024)


def _peak_rss_mb() -> float:
    """Return peak RSS in MB (Linux: ru_maxrss is in KB)."""
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _system_info() -> dict:
    """Snapshot of system resources for command_start events."""
    mem = psutil.virtual_memory()
    try:
        disk = os.statvfs("/")
        disk_gb = round(disk.f_frsize * disk.f_blocks / (1024 ** 3), 1)
    except OSError:
        disk_gb = 0.0
    return {
        "cpu_count": psutil.cpu_count(),
        "ram_gb": round(mem.total / (1024 ** 3), 1),
        "disk_gb": disk_gb,
    }


# ---------------------------------------------------------------------------
# TelemetryRecorder
# ---------------------------------------------------------------------------

class TelemetryRecorder:
    """Writes JSONL events to a file.

    Instantiated once per CLI invocation and passed through Click context.
    All modules receive it via dependency injection (``ctx.obj["telemetry"]``).
    """

    def __init__(self, path: Path, command: str | None = None) -> None:
        self._path = path
        self._command = command
        path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(path, "a")  # noqa: SIM115

    def emit(self, event: str, data: dict | None = None) -> None:
        """Write one event to the JSONL stream."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "event": event,
            "command": self._command,
            **(data or {}),
        }
        self._file.write(json.dumps(record, default=str) + "\n")
        self._file.flush()

    def close(self) -> None:
        """Flush and close the underlying file."""
        if not self._file.closed:
            self._file.close()


class NullTelemetryRecorder(TelemetryRecorder):
    """No-op recorder for when telemetry is disabled or unavailable."""

    def __init__(self) -> None:
        self._path = None
        self._command = None
        self._file = None  # type: ignore[assignment]

    def emit(self, event: str, data: dict | None = None) -> None:
        pass

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Per-command profiling context manager
# ---------------------------------------------------------------------------

@contextmanager
def command_span(telemetry: TelemetryRecorder, args: dict):
    """Context manager that emits ``command_start`` / ``command_end`` events.

    Yields a mutable *counters* dict that the caller populates with
    command-specific metrics (e.g. ``rows``, ``files``).  These are
    included in the ``command_end`` event and printed as a human-readable
    summary line.
    """
    telemetry.emit("command_start", {
        "args": args,
        "system": _system_info(),
    })
    t0 = time.perf_counter()
    start_rss = _current_rss_mb()
    counters: dict = {}
    exit_code = 0

    try:
        yield counters
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else 1
        raise
    except Exception:
        exit_code = 1
        raise
    finally:
        elapsed = time.perf_counter() - t0
        peak = _peak_rss_mb()
        telemetry.emit("command_end", {
            "wall_seconds": round(elapsed, 2),
            "peak_rss_mb": round(peak, 1),
            "start_rss_mb": round(start_rss, 1),
            "exit_code": exit_code,
            "counters": counters,
        })

        # Human-readable summary
        parts = f"[dim]⏱ {elapsed:.1f}s · peak {peak:.0f} MB"
        if counters:
            parts += "".join(f" · {k}: {v}" for k, v in counters.items())
        parts += "[/dim]"
        display.console.print(f"\n{parts}")
