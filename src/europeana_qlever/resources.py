"""Auto-detect system resources and compute allocations for pipeline stages.

Provides a :class:`ResourceBudget` that inspects CPU, memory, disk, and
terminal at runtime and derives sensible defaults for every resource
parameter in the pipeline — worker counts, buffer sizes, memory limits,
timeouts, monitoring intervals, and more.

Every value is:
1. **Computed** from detected system resources
2. **Bounded** by reasonable hardcoded min/max (the fallback)
3. **Overridable** via CLI flags where applicable
4. **Documented** in the :meth:`summary_table` output
"""

from __future__ import annotations

import math
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import psutil
from rich.table import Table


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to [lo, hi]."""
    return max(lo, min(value, hi))


def _round_gb(gb: float) -> int:
    """Round GB to the nearest integer, minimum 1."""
    return max(1, math.floor(gb))


def _fmt_bytes(n: int) -> str:
    """Human-readable byte size."""
    if n >= 1_048_576:
        return f"{n / 1_048_576:.0f} MB"
    return f"{n / 1024:.0f} KB"


@dataclass
class ResourceBudget:
    """Detected system resources and derived allocations.

    Use :meth:`detect` to create an instance from the current machine state.
    """

    total_memory_gb: float
    available_memory_gb: float
    cpu_count: int
    disk_free_gb: float
    terminal_height: int

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def detect(cls, work_dir: Path) -> ResourceBudget:
        """Snapshot current system resources."""
        mem = psutil.virtual_memory()
        try:
            disk = shutil.disk_usage(work_dir)
            disk_free_gb = disk.free / (1024**3)
        except OSError:
            disk_free_gb = 0.0

        term = shutil.get_terminal_size((80, 24))

        return cls(
            total_memory_gb=mem.total / (1024**3),
            available_memory_gb=mem.available / (1024**3),
            cpu_count=os.cpu_count() or 4,
            disk_free_gb=disk_free_gb,
            terminal_height=term.lines,
        )

    # ==================================================================
    # Merge stage
    # ==================================================================

    def merge_workers(self) -> int:
        """Worker count for the merge stage (ProcessPoolExecutor).

        Heuristic: ``cpu_count`` (CPU-bound rdflib validation in processes),
        bounded by available memory (~250 MB per process). Floor of 4.
        """
        by_cpu = self.cpu_count
        by_mem = int(self.available_memory_gb / 0.25)
        return max(4, min(by_cpu, by_mem))

    def merge_initial_concurrency(self, workers: int) -> int:
        """Initial concurrency permits: ``workers // 2``, floor of 4."""
        return max(4, workers // 2)

    def merge_queue_size(self, workers: int) -> int:
        """Writer queue maxsize: ``workers * 2``, minimum 4."""
        return max(4, workers * 2)

    def bulk_read_size(self) -> int:
        """ZIP entry bulk read buffer.

        0.1% of available RAM, clamped to 64 KB – 1 MB.
        """
        raw = int(self.available_memory_gb * 1024 * 1024 * 1024 * 0.001)
        return int(_clamp(raw, 65_536, 1_048_576))

    def copy_buf_size(self) -> int:
        """Temp-to-chunk file copy buffer.

        0.5% of available RAM, clamped to 1 MB – 32 MB.
        """
        raw = int(self.available_memory_gb * 1024 * 1024 * 1024 * 0.005)
        return int(_clamp(raw, 1_048_576, 33_554_432))

    def merge_chunk_size_gb(self) -> float:
        """Target chunk file size.

        1% of free disk space, clamped to 1–10 GB.
        """
        return round(_clamp(self.disk_free_gb * 0.01, 1.0, 10.0), 1)

    def backpressure_thresholds(self) -> tuple[float, float, float]:
        """(soft, warn, critical) memory percentage thresholds.

        On low-memory systems (<8 GB): (60, 70, 85).
        Normal: (70, 80, 90).
        """
        if self.total_memory_gb < 8:
            return (60.0, 70.0, 85.0)
        return (70.0, 80.0, 90.0)

    def backpressure_sleeps(self) -> tuple[float, float]:
        """(soft_sleep, warn_sleep) in seconds."""
        return (0.1, 0.5)

    def cpu_target_pct(self) -> float:
        """CPU % above which adaptive throttle reduces concurrency. Default 85%."""
        return 85.0

    def cpu_low_pct(self) -> float:
        """CPU % below which adaptive throttle increases concurrency. Default 65%."""
        return 65.0

    def throttle_consecutive_samples(self) -> int:
        """Consecutive samples before throttle adjusts. Default 3."""
        return 3

    def writer_join_timeout(self) -> int:
        """Writer thread join timeout in seconds. Default 300."""
        return 300

    # ==================================================================
    # QLever engine
    # ==================================================================

    def qlever_stxxl(self) -> str:
        """STXXL (external sort) memory: 25% of available, min 2 GB."""
        gb = self.available_memory_gb * 0.25
        return f"{_round_gb(max(gb, 2.0))}G"

    def qlever_query_memory(self) -> str:
        """Query execution memory: 45% of available, min 4 GB."""
        gb = self.available_memory_gb * 0.45
        return f"{_round_gb(max(gb, 4.0))}G"

    def qlever_cache(self) -> str:
        """Query cache size: 15% of available, min 2 GB."""
        gb = self.available_memory_gb * 0.15
        return f"{_round_gb(max(gb, 2.0))}G"

    def qlever_cache_single_entry(self) -> str:
        """Max single cache entry: 7.5% of available, min 1 GB."""
        gb = self.available_memory_gb * 0.075
        return f"{_round_gb(max(gb, 1.0))}G"

    def qlever_triples_per_batch(self) -> int:
        """Index batch size: ~200 bytes/triple, 2% of available RAM.

        Clamped to 1M–10M.
        """
        bytes_budget = self.available_memory_gb * 1024**3 * 0.02
        triples = int(bytes_budget / 200)
        return int(_clamp(triples, 1_000_000, 10_000_000))

    def qlever_timeout(self) -> int:
        """Query timeout for Qleverfile in seconds. Default 600."""
        return 600

    def qlever_threads(self) -> int:
        """QLever worker threads: half of CPU count, min 2."""
        return max(2, self.cpu_count // 2)

    # ==================================================================
    # Export / DuckDB
    # ==================================================================

    def duckdb_memory(self) -> str:
        """DuckDB memory budget: 15% of available, 1–8 GB."""
        gb = self.available_memory_gb * 0.15
        return f"{_round_gb(_clamp(gb, 1.0, 8.0))}G"

    def duckdb_sample_size(self) -> int:
        """DuckDB type inference sample size. Default 100K."""
        return 100_000

    def duckdb_row_group_size(self) -> int:
        """Parquet row group size. Default 100K."""
        return 100_000

    def http_chunk_size(self) -> int:
        """HTTP streaming chunk size.

        0.1% of available RAM, clamped to 256 KB – 4 MB.
        """
        raw = int(self.available_memory_gb * 1024 * 1024 * 1024 * 0.001)
        return int(_clamp(raw, 262_144, 4_194_304))

    def http_connect_timeout(self) -> int:
        """HTTP connect timeout in seconds. Default 30."""
        return 30

    def export_timeout(self) -> int:
        """Per-query export timeout in seconds. Default 3600."""
        return 3600

    def export_max_retries(self) -> int:
        """Max export retry attempts. Default 2."""
        return 2

    def export_retry_delays(self) -> tuple[int, ...]:
        """Seconds between retry attempts. Default (5, 15)."""
        return (5, 15)

    # ==================================================================
    # Monitoring
    # ==================================================================

    def monitor_idle_interval(self) -> float:
        """Resource monitor idle sample interval in seconds. Default 2.0."""
        return 2.0

    def monitor_active_interval(self) -> float:
        """Resource monitor active sample interval in seconds. Default 1.0."""
        return 1.0

    def monitor_warn_pct(self) -> float:
        """Memory warning threshold percentage.

        On low-memory systems (<8 GB): 70%. Normal: 80%.
        """
        return 70.0 if self.total_memory_gb < 8 else 80.0

    def monitor_critical_pct(self) -> float:
        """Memory critical threshold percentage.

        On low-memory systems (<8 GB): 85%. Normal: 90%.
        """
        return 85.0 if self.total_memory_gb < 8 else 90.0

    # ==================================================================
    # Logging
    # ==================================================================

    def log_max_bytes(self) -> int:
        """Log file rotation threshold. Default 50 MB."""
        return 50_000_000

    def log_backup_count(self) -> int:
        """Number of backup log files. Default 3."""
        return 3

    # ==================================================================
    # Dashboard
    # ==================================================================

    def dashboard_log_lines(self) -> int:
        """Log tail lines in dashboard.

        ``terminal_height - 14`` (room for panels), clamped to 4–30.
        """
        return int(_clamp(self.terminal_height - 14, 4, 30))

    def dashboard_refresh_rate(self) -> int:
        """Dashboard refresh rate in Hz. Default 2."""
        return 2

    # ==================================================================
    # Display
    # ==================================================================

    def summary_table(self) -> Table:
        """Rich table summarising all detected resources and derived settings."""
        tbl = Table(
            title="Resource Budget",
            title_style="bold",
            show_header=True,
            header_style="dim",
            padding=(0, 1),
        )
        tbl.add_column("Parameter", style="cyan")
        tbl.add_column("Value", justify="right")
        tbl.add_column("Source", style="dim")

        # --- System ---
        tbl.add_row("CPUs", str(self.cpu_count), "detected")
        tbl.add_row("Total RAM", f"{self.total_memory_gb:.1f} GB", "detected")
        tbl.add_row("Available RAM", f"{self.available_memory_gb:.1f} GB", "detected")
        tbl.add_row("Disk free", f"{self.disk_free_gb:.0f} GB", "detected")
        tbl.add_row("Terminal height", f"{self.terminal_height} lines", "detected")

        tbl.add_section()

        # --- Merge ---
        workers = self.merge_workers()
        bp = self.backpressure_thresholds()
        tbl.add_row("Merge workers", str(workers), "auto")
        tbl.add_row("Bulk read buffer", _fmt_bytes(self.bulk_read_size()), "auto")
        tbl.add_row("Copy buffer", _fmt_bytes(self.copy_buf_size()), "auto")
        tbl.add_row("Chunk size", f"{self.merge_chunk_size_gb()} GB", "auto")
        tbl.add_row("Backpressure", f"{bp[0]:.0f}/{bp[1]:.0f}/{bp[2]:.0f}%", "auto")
        tbl.add_row(
            "CPU throttle",
            f"{self.cpu_low_pct():.0f}–{self.cpu_target_pct():.0f}%",
            "auto",
        )

        tbl.add_section()

        # --- QLever ---
        tbl.add_row("QLever stxxl", self.qlever_stxxl(), "auto")
        tbl.add_row("QLever query", self.qlever_query_memory(), "auto")
        tbl.add_row("QLever cache", self.qlever_cache(), "auto")
        tbl.add_row("QLever cache entry", self.qlever_cache_single_entry(), "auto")
        tbl.add_row("Triples/batch", f"{self.qlever_triples_per_batch():,}", "auto")
        tbl.add_row("QLever timeout", f"{self.qlever_timeout()}s", "default")
        tbl.add_row("QLever threads", str(self.qlever_threads()), "auto")

        tbl.add_section()

        # --- Export ---
        tbl.add_row("DuckDB memory", self.duckdb_memory(), "auto")
        tbl.add_row("HTTP chunk", _fmt_bytes(self.http_chunk_size()), "auto")
        tbl.add_row("Row group size", f"{self.duckdb_row_group_size():,}", "default")
        tbl.add_row("Export timeout", f"{self.export_timeout()}s", "default")

        tbl.add_section()

        # --- Monitoring ---
        tbl.add_row("Idle interval", f"{self.monitor_idle_interval()}s", "default")
        tbl.add_row("Active interval", f"{self.monitor_active_interval()}s", "default")
        tbl.add_row("Warn threshold", f"{self.monitor_warn_pct():.0f}%", "auto")
        tbl.add_row("Critical threshold", f"{self.monitor_critical_pct():.0f}%", "auto")
        tbl.add_row("Dashboard log", f"{self.dashboard_log_lines()} lines", "auto")

        return tbl
