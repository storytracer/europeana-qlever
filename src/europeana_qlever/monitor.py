"""Background resource monitor for memory, disk, CPU, and process tracking.

Runs as a daemon thread, sampling system resources at a configurable
interval.  Logs every sample to a CSV file and prints Rich console
warnings when memory usage crosses configurable thresholds.  Provides
a backpressure API so that memory-hungry stages (e.g. merge) can pause
when the system is under pressure.
"""

from __future__ import annotations

import csv
import logging
import shutil
import threading
import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import psutil

from . import display

if TYPE_CHECKING:
    from rich.console import Console

logger = logging.getLogger(__name__)

from .constants import (
    DEFAULT_MONITOR_CRITICAL_MEMORY_PCT,
    DEFAULT_MONITOR_INTERVAL_ACTIVE_SECONDS,
    DEFAULT_MONITOR_INTERVAL_SECONDS,
    DEFAULT_MONITOR_WARN_MEMORY_PCT,
)

_CSV_HEADER = [
    "timestamp", "rss_mb", "available_mb", "total_mb",
    "memory_pct", "disk_free_gb", "disk_total_gb",
    "cpu_pct", "swap_used_gb", "swap_total_gb",
    "process_cpu_pct", "process_rss_mb", "child_count",
]


@dataclass(frozen=True)
class ResourceSnapshot:
    """Point-in-time resource reading."""

    timestamp: float
    rss_mb: float
    available_mb: float
    total_mb: float
    memory_pct: float  # system-wide used %
    disk_free_gb: float
    disk_total_gb: float
    cpu_pct: float  # system-wide CPU %
    swap_used_gb: float
    swap_total_gb: float
    # Process-group metrics (main + child processes)
    process_cpu_pct: float = 0.0  # our tool's CPU, normalized to 0-100%
    process_rss_mb: float = 0.0  # total RSS across main + children
    child_count: int = 0  # number of child processes


class ResourceMonitor:
    """Background daemon that samples memory, CPU, and disk usage.

    Usage::

        with ResourceMonitor(work_dir, console=console) as mon:
            if mon.is_memory_critical():
                mon.wait_for_memory()
            ...
    """

    def __init__(
        self,
        work_dir: Path,
        *,
        interval: float = DEFAULT_MONITOR_INTERVAL_SECONDS,
        active_interval: float = DEFAULT_MONITOR_INTERVAL_ACTIVE_SECONDS,
        warn_pct: float = DEFAULT_MONITOR_WARN_MEMORY_PCT,
        critical_pct: float = DEFAULT_MONITOR_CRITICAL_MEMORY_PCT,
        log_file: Path | None = None,
        console: Console | None = None,
    ) -> None:
        self._work_dir = work_dir
        self._idle_interval = interval
        self._active_interval = active_interval
        self._interval = interval
        self._warn_pct = warn_pct
        self._critical_pct = critical_pct
        self._log_path = log_file or (work_dir / "monitor.log")
        self._console = console or display.console

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._process = psutil.Process()

        # Cache of child psutil.Process objects keyed by PID.
        # Reusing the same objects across samples is required because
        # psutil.Process.cpu_percent() computes a delta between calls —
        # the first call on a new object always returns 0.
        self._children_cache: dict[int, psutil.Process] = {}

        # Tracking
        self._peak_rss_mb: float = 0.0
        self._min_available_mb: float = float("inf")
        self._last_state: str = "ok"  # ok | warn | critical
        self._lock = threading.Lock()
        self._latest: ResourceSnapshot | None = None

        # Memory recovery event — set when memory drops below warn threshold
        self._memory_ok = threading.Event()
        self._memory_ok.set()

        # Dashboard callback (set by Dashboard to receive updates)
        self._on_sample: callable | None = None

    # -- Context manager --------------------------------------------------

    def __enter__(self) -> ResourceMonitor:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # -- Lifecycle ---------------------------------------------------------

    def start(self) -> None:
        # Prime cpu_percent (first call always returns 0)
        psutil.cpu_percent(interval=None)
        self._process.cpu_percent(interval=None)

        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        # Write CSV header
        with open(self._log_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(_CSV_HEADER)
        self._thread = threading.Thread(
            target=self._run, name="resource-monitor", daemon=True,
        )
        self._thread.start()
        self._console.print(
            f"[dim]Resource monitor started "
            f"(interval={self._interval}s, log={self._log_path})[/dim]"
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 2)

        # Print summary
        snap = self.snapshot()
        self._console.print(
            f"\n[dim]Resource monitor summary: "
            f"peak RSS {self._peak_rss_mb:.0f} MB, "
            f"min available {self._min_available_mb:.0f} MB, "
            f"disk free {snap.disk_free_gb:.1f} GB[/dim]"
        )

    # -- Public API --------------------------------------------------------

    @property
    def latest(self) -> ResourceSnapshot | None:
        """Most recent cached snapshot (read without extra syscalls)."""
        with self._lock:
            return self._latest

    def set_active(self, active: bool) -> None:
        """Switch to faster sampling during active work."""
        self._interval = self._active_interval if active else self._idle_interval

    def snapshot(self) -> ResourceSnapshot:
        """Take a resource reading right now."""
        mem = psutil.virtual_memory()
        proc_mem = self._process.memory_info()
        rss = proc_mem.rss / (1024 * 1024)
        cpu = psutil.cpu_percent(interval=None)
        swap = psutil.swap_memory()
        try:
            disk = shutil.disk_usage(self._work_dir)
            disk_free_gb = disk.free / (1024 ** 3)
            disk_total_gb = disk.total / (1024 ** 3)
        except OSError:
            disk_free_gb = 0.0
            disk_total_gb = 0.0

        # Process-group metrics (main + child processes).
        # Reuse cached psutil.Process objects so cpu_percent() has a
        # previous baseline — first call on a new object always returns 0.
        proc_cpu = self._process.cpu_percent(interval=None)
        proc_rss = proc_mem.rss
        live_pids: set[int] = set()
        try:
            children = self._process.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            children = []
        for child in children:
            pid = child.pid
            live_pids.add(pid)
            cached = self._children_cache.get(pid)
            if cached is None:
                # New child — prime it (returns 0 this time, real value next)
                try:
                    child.cpu_percent(interval=None)
                    child.memory_info()  # warm up
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                self._children_cache[pid] = child
                # Still count its RSS, just not its CPU (unprimed)
                try:
                    proc_rss += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            else:
                try:
                    proc_cpu += cached.cpu_percent(interval=None)
                    proc_rss += cached.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        # Evict dead children from cache
        dead = set(self._children_cache) - live_pids
        for pid in dead:
            del self._children_cache[pid]
        child_count = len(live_pids)
        cpu_count = psutil.cpu_count() or 1
        process_cpu_pct = min(100.0, proc_cpu / cpu_count)

        return ResourceSnapshot(
            timestamp=time.time(),
            rss_mb=rss,
            available_mb=mem.available / (1024 * 1024),
            total_mb=mem.total / (1024 * 1024),
            memory_pct=mem.percent,
            disk_free_gb=disk_free_gb,
            disk_total_gb=disk_total_gb,
            cpu_pct=cpu,
            swap_used_gb=swap.used / (1024 ** 3),
            swap_total_gb=swap.total / (1024 ** 3),
            process_cpu_pct=process_cpu_pct,
            process_rss_mb=proc_rss / (1024 * 1024),
            child_count=child_count,
        )

    def is_memory_critical(self) -> bool:
        """True if system memory usage is above the critical threshold.

        Always takes a fresh reading to avoid acting on stale data.
        """
        snap = self.snapshot()
        return snap.memory_pct >= self._critical_pct

    def memory_pct(self) -> float:
        """Return current system memory usage percentage (fresh read)."""
        snap = self.snapshot()
        return snap.memory_pct

    def wait_for_memory(self, timeout: float = 120.0) -> bool:
        """Block until memory drops below the warning threshold.

        Returns True if memory recovered, False on timeout.
        """
        if self._memory_ok.is_set():
            return True
        self._console.print(
            "[yellow]Memory pressure: pausing until usage drops "
            f"below {self._warn_pct:.0f}%…[/yellow]"
        )
        return self._memory_ok.wait(timeout=timeout)

    # -- Background loop ---------------------------------------------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            snap = self.snapshot()

            # Update tracking
            with self._lock:
                self._latest = snap
                if snap.rss_mb > self._peak_rss_mb:
                    self._peak_rss_mb = snap.rss_mb
                if snap.available_mb < self._min_available_mb:
                    self._min_available_mb = snap.available_mb

            # Append to log file
            self._log_sample(snap)

            # State transitions for console warnings
            new_state = self._classify(snap.memory_pct)
            if new_state != self._last_state:
                self._emit_transition(self._last_state, new_state, snap)
                self._last_state = new_state

            # Backpressure signalling
            if snap.memory_pct >= self._warn_pct:
                self._memory_ok.clear()
            else:
                self._memory_ok.set()

            # Notify dashboard if attached
            if self._on_sample is not None:
                try:
                    self._on_sample(snap)
                except Exception:
                    pass  # never let dashboard errors kill the monitor

            self._stop_event.wait(self._interval)

    def _classify(self, pct: float) -> str:
        if pct >= self._critical_pct:
            return "critical"
        if pct >= self._warn_pct:
            return "warn"
        return "ok"

    def _emit_transition(
        self, old: str, new: str, snap: ResourceSnapshot,
    ) -> None:
        msg = (
            f"Memory {new}: {snap.memory_pct:.1f}% used "
            f"(RSS {snap.rss_mb:.0f} MB, available {snap.available_mb:.0f} MB)"
        )
        if new == "critical":
            self._console.print(f"[red bold]{msg}[/red bold]")
            logger.warning(msg)
        elif new == "warn":
            self._console.print(f"[yellow]{msg}[/yellow]")
            logger.warning(msg)
        elif new == "ok" and old in ("warn", "critical"):
            self._console.print(
                f"[green]Memory recovered: {snap.memory_pct:.1f}% used "
                f"(available {snap.available_mb:.0f} MB)[/green]"
            )
            logger.info(msg)

    def _log_sample(self, snap: ResourceSnapshot) -> None:
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow([
            f"{snap.timestamp:.1f}",
            f"{snap.rss_mb:.1f}",
            f"{snap.available_mb:.1f}",
            f"{snap.total_mb:.1f}",
            f"{snap.memory_pct:.1f}",
            f"{snap.disk_free_gb:.2f}",
            f"{snap.disk_total_gb:.2f}",
            f"{snap.cpu_pct:.1f}",
            f"{snap.swap_used_gb:.2f}",
            f"{snap.swap_total_gb:.2f}",
            f"{snap.process_cpu_pct:.1f}",
            f"{snap.process_rss_mb:.1f}",
            f"{snap.child_count}",
        ])
        with open(self._log_path, "a") as f:
            f.write(buf.getvalue())
