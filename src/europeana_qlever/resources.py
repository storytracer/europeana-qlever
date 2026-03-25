"""Auto-detect system resources and compute allocations for pipeline stages.

Provides a :class:`ResourceBudget` that inspects CPU, memory, and disk at
runtime and derives sensible defaults for worker counts, memory limits, and
QLever configuration — ensuring the pipeline uses available capacity without
exhausting the machine.
"""

from __future__ import annotations

import math
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import psutil
from rich.table import Table


@dataclass
class ResourceBudget:
    """Detected system resources and derived allocations.

    Use :meth:`detect` to create an instance from the current machine state.
    All ``*_memory`` helpers return human-readable strings like ``"8G"``
    suitable for passing directly to QLever / DuckDB CLI options.
    """

    total_memory_gb: float
    available_memory_gb: float
    cpu_count: int
    disk_free_gb: float

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

        return cls(
            total_memory_gb=mem.total / (1024**3),
            available_memory_gb=mem.available / (1024**3),
            cpu_count=os.cpu_count() or 4,
            disk_free_gb=disk_free_gb,
        )

    # ------------------------------------------------------------------
    # Merge stage
    # ------------------------------------------------------------------

    def merge_workers(self) -> int:
        """Compute worker count for the I/O-bound merge stage.

        Heuristic: up to ``cpu * 2`` (I/O-bound work benefits from
        over-subscription), capped by available memory (~150 MB per worker)
        and a hard ceiling of 32.  Floor of 4.
        """
        by_cpu = min(self.cpu_count * 2, 32)
        by_mem = int(self.available_memory_gb / 0.15)
        return max(4, min(by_cpu, by_mem))

    def merge_semaphore(self, workers: int) -> int:
        """Semaphore permits for the merge submission loop."""
        return workers * 3

    # ------------------------------------------------------------------
    # DuckDB (export stage)
    # ------------------------------------------------------------------

    def duckdb_memory(self) -> str:
        """DuckDB memory budget: 15% of available, 1–8 GB."""
        gb = self.available_memory_gb * 0.15
        gb = max(1.0, min(gb, 8.0))
        return f"{_round_gb(gb)}G"

    # ------------------------------------------------------------------
    # QLever engine
    # ------------------------------------------------------------------

    def qlever_stxxl(self) -> str:
        """STXXL (external sort) memory: 25% of total, 2–16 GB."""
        gb = self.total_memory_gb * 0.25
        gb = max(2.0, min(gb, 16.0))
        return f"{_round_gb(gb)}G"

    def qlever_query_memory(self) -> str:
        """Query execution memory: 20% of total, 2–12 GB."""
        gb = self.total_memory_gb * 0.20
        gb = max(2.0, min(gb, 12.0))
        return f"{_round_gb(gb)}G"

    def qlever_cache(self) -> str:
        """Query cache size: 10% of total, 1–8 GB."""
        gb = self.total_memory_gb * 0.10
        gb = max(1.0, min(gb, 8.0))
        return f"{_round_gb(gb)}G"

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def summary_table(self) -> Table:
        """Rich table summarising detected resources and derived settings."""
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

        # Detected
        tbl.add_row("CPUs", str(self.cpu_count), "detected")
        tbl.add_row("Total RAM", f"{self.total_memory_gb:.1f} GB", "detected")
        tbl.add_row("Available RAM", f"{self.available_memory_gb:.1f} GB", "detected")
        tbl.add_row("Disk free", f"{self.disk_free_gb:.0f} GB", "detected")

        tbl.add_section()

        # Derived
        workers = self.merge_workers()
        tbl.add_row("Merge workers", str(workers), "auto")
        tbl.add_row("DuckDB memory", self.duckdb_memory(), "auto")
        tbl.add_row("QLever stxxl", self.qlever_stxxl(), "auto")
        tbl.add_row("QLever query", self.qlever_query_memory(), "auto")
        tbl.add_row("QLever cache", self.qlever_cache(), "auto")

        return tbl


def _round_gb(gb: float) -> int:
    """Round GB to the nearest integer, minimum 1."""
    return max(1, math.floor(gb))
