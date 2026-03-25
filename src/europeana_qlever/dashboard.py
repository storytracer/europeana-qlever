"""Live pipeline dashboard using Rich Live + Layout.

Provides an htop-style HUD that displays system resources, pipeline
progress, and a live log tail — all in a single auto-updating terminal
layout.

The :class:`Dashboard` is designed for the ``pipeline`` command.  Standalone
commands (``merge``, ``export``) continue to use their own Progress bars.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

from . import display

if TYPE_CHECKING:
    from .monitor import ResourceMonitor, ResourceSnapshot

logger = logging.getLogger(__name__)

# Total pipeline stages
_STAGE_NAMES = ["Merge", "Qleverfile", "Index", "Start", "Export"]
_DEFAULT_MAX_LOG_LINES = 12


def _pct_bar(
    label: str, pct: float, used: str, total: str, style: str,
    warn_pct: float = 70.0, critical_pct: float = 90.0,
) -> Text:
    """Render a single-line resource bar like: MEM ████░░ 58% 37/64G."""
    width = 10
    filled = int(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)

    # Color the bar based on usage thresholds
    if pct >= critical_pct:
        bar_style = "red bold"
    elif pct >= warn_pct:
        bar_style = "yellow"
    else:
        bar_style = style

    line = Text()
    line.append(f" {label:4s} ", style="bold")
    line.append(bar, style=bar_style)
    line.append(f" {pct:4.0f}%  ", style="dim")
    line.append(f"{used}/{total}", style="dim")
    return line


def _format_gb(gb: float) -> str:
    """Format GB value compactly."""
    if gb >= 100:
        return f"{gb:.0f}G"
    if gb >= 10:
        return f"{gb:.0f}G"
    return f"{gb:.1f}G"


class _LogCapture:
    """File-like object that routes written lines to :meth:`Dashboard.log`.

    Used as the ``file`` argument of a :class:`~rich.console.Console` so that
    all ``display.console.print()`` calls are redirected into the dashboard
    log tail when the dashboard is active.
    """

    def __init__(self, dashboard: Dashboard) -> None:
        self._dashboard = dashboard
        self._buffer = ""

    def write(self, text: str) -> int:
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if line:
                self._dashboard.log(line)
        return len(text)

    def flush(self) -> None:
        if self._buffer.strip():
            self._dashboard.log(self._buffer.strip())
            self._buffer = ""


class DashboardLogHandler(logging.Handler):
    """Logging handler that captures formatted log lines for the dashboard."""

    def __init__(self, log_lines: deque[str], lock: threading.Lock) -> None:
        super().__init__()
        self._log_lines = log_lines
        self._lock = lock
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            with self._lock:
                self._log_lines.append(msg)
        except Exception:
            pass


@dataclass
class Dashboard:
    """Live pipeline dashboard with system resources, progress, and log tail.

    Usage::

        with Dashboard(monitor) as dash:
            dash.set_stage("Merge", total=2272)
            for i in range(2272):
                ...
                dash.advance()
            dash.complete_stage()
    """

    monitor: ResourceMonitor
    max_log_lines: int = _DEFAULT_MAX_LOG_LINES
    refresh_rate: int = 2
    _live: Live | None = field(default=None, init=False, repr=False)
    _progress: Progress = field(init=False, repr=False)
    _overall_task: TaskID | None = field(default=None, init=False, repr=False)
    _stage_task: TaskID | None = field(default=None, init=False, repr=False)
    _current_stage: str = field(default="", init=False)
    _current_stage_idx: int = field(default=0, init=False)
    _info: dict[str, str] = field(default_factory=dict, init=False)
    _log_lines: deque[str] = field(init=False, repr=False)
    _log_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _log_handler: DashboardLogHandler | None = field(default=None, init=False, repr=False)
    _last_snap: ResourceSnapshot | None = field(default=None, init=False, repr=False)
    _original_console: Console | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._log_lines = deque(maxlen=self.max_log_lines)
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("·"),
            TimeElapsedColumn(),
            TextColumn("·"),
            TimeRemainingColumn(),
        )
        self._overall_task = self._progress.add_task(
            "Pipeline", total=len(_STAGE_NAMES),
        )

    def __enter__(self) -> Dashboard:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def start(self) -> None:
        """Activate the live display and attach the log handler."""
        # Attach log handler to capture pipeline logs
        self._log_handler = DashboardLogHandler(self._log_lines, self._log_lock)
        self._log_handler.setLevel(logging.INFO)
        root_logger = logging.getLogger("europeana_qlever")
        root_logger.addHandler(self._log_handler)

        # Hook into monitor's sample callback for auto-refresh
        self.monitor._on_sample = self._on_monitor_sample

        # Redirect display.console output into the dashboard log tail so that
        # all display.console.print() calls (from merge, export, cli) and any
        # subprocess output routed through it appear in the log panel instead
        # of writing directly to the terminal (which causes flickering).
        self._original_console = display.console
        capture = _LogCapture(self)
        display.console = Console(
            file=capture, width=self._original_console.width,
            highlight=False, no_color=True,
        )

        layout = self._build_layout()
        self._live = Live(
            layout,
            console=self._original_console,
            refresh_per_second=self.refresh_rate,
            screen=False,
        )
        self._live.start()

    def stop(self) -> None:
        """Tear down the live display and detach the log handler."""
        if self._live is not None:
            self._live.stop()
            self._live = None

        # Detach log handler
        if self._log_handler is not None:
            root_logger = logging.getLogger("europeana_qlever")
            root_logger.removeHandler(self._log_handler)
            self._log_handler = None

        # Restore original console
        if self._original_console is not None:
            display.console = self._original_console
            self._original_console = None

        # Unhook monitor callback
        self.monitor._on_sample = None

    # -- Public API --------------------------------------------------------

    def set_stage(self, name: str, total: int | None = None) -> None:
        """Begin a new pipeline stage."""
        self._current_stage = name
        try:
            self._current_stage_idx = _STAGE_NAMES.index(name) + 1
        except ValueError:
            self._current_stage_idx += 1

        # Remove old stage task, add new one
        if self._stage_task is not None:
            self._progress.remove_task(self._stage_task)
        self._stage_task = self._progress.add_task(
            name, total=total,
        )
        self._info.clear()
        self._refresh()

    def advance(self, n: int = 1) -> None:
        """Advance the current stage progress bar."""
        if self._stage_task is not None:
            self._progress.advance(self._stage_task, n)
        self._refresh()

    def complete_stage(self) -> None:
        """Mark the current stage as complete and advance overall."""
        if self._stage_task is not None:
            task_obj = self._progress._tasks.get(self._stage_task)
            if task_obj is not None and task_obj.total is not None:
                self._progress.update(self._stage_task, completed=task_obj.total)
        self._progress.advance(self._overall_task)
        self._refresh()

    def set_info(self, key: str, value: object) -> None:
        """Set a tool metric displayed in the system panel."""
        self._info[key] = str(value)
        self._refresh()

    def log(self, message: str) -> None:
        """Add a message to the log tail."""
        ts = time.strftime("%H:%M:%S")
        with self._log_lock:
            self._log_lines.append(f"{ts} INFO  {message}")
        self._refresh()

    # -- Internal ----------------------------------------------------------

    def _on_monitor_sample(self, snap: ResourceSnapshot) -> None:
        """Called by the monitor thread on each sample."""
        self._last_snap = snap
        self._refresh()

    def _refresh(self) -> None:
        """Update the live display."""
        if self._live is None:
            return
        try:
            self._live.update(self._build_layout())
        except Exception:
            pass  # never crash on display errors

    def _build_layout(self) -> Layout:
        """Construct the full dashboard layout."""
        narrow = display.is_narrow()

        layout = Layout()

        if narrow:
            # Narrow: stack vertically, skip system panel
            layout.split_column(
                Layout(self._build_progress_panel(), name="progress", size=8),
                Layout(self._build_log_panel(), name="log"),
            )
        else:
            top = Layout(size=10)
            top.split_row(
                Layout(self._build_system_panel(), name="system", ratio=1),
                Layout(self._build_progress_panel(), name="progress", ratio=1),
            )
            layout.split_column(
                top,
                Layout(self._build_log_panel(), name="log"),
            )

        return layout

    def _build_system_panel(self) -> Panel:
        """Build the system resources panel."""
        snap = self._last_snap
        if snap is None:
            snap = self.monitor.latest
        if snap is None:
            snap = self.monitor.snapshot()

        lines: list[Text] = []

        # Read thresholds from monitor (dynamic, not hardcoded)
        warn = self.monitor._warn_pct
        crit = self.monitor._critical_pct

        # CPU
        cpus = os.cpu_count() or 1
        lines.append(_pct_bar(
            "CPU", snap.cpu_pct,
            f"{snap.cpu_pct:.0f}%", f"{cpus}C",
            "green", warn_pct=warn, critical_pct=crit,
        ))

        # Memory
        used_gb = (snap.total_mb - snap.available_mb) / 1024
        total_gb = snap.total_mb / 1024
        lines.append(_pct_bar(
            "MEM", snap.memory_pct,
            _format_gb(used_gb), _format_gb(total_gb),
            "blue", warn_pct=warn, critical_pct=crit,
        ))

        # Disk
        disk_used_gb = snap.disk_total_gb - snap.disk_free_gb
        disk_pct = (disk_used_gb / snap.disk_total_gb * 100) if snap.disk_total_gb > 0 else 0
        lines.append(_pct_bar(
            "DISK", disk_pct,
            _format_gb(snap.disk_free_gb), _format_gb(snap.disk_total_gb),
            "magenta", warn_pct=warn, critical_pct=crit,
        ))

        # Swap
        swap_pct = (snap.swap_used_gb / snap.swap_total_gb * 100) if snap.swap_total_gb > 0 else 0
        lines.append(_pct_bar(
            "SWAP", swap_pct,
            _format_gb(snap.swap_used_gb), _format_gb(snap.swap_total_gb),
            "cyan", warn_pct=warn, critical_pct=crit,
        ))

        # Tool metrics
        if self._info:
            lines.append(Text())
            for k, v in self._info.items():
                line = Text()
                line.append(f" {k}: ", style="bold")
                line.append(v, style="dim")
                lines.append(line)

        # RSS
        rss_line = Text()
        rss_line.append(" RSS: ", style="bold")
        rss_line.append(f"{snap.rss_mb:.0f} MB", style="dim")
        lines.append(rss_line)

        content = Text("\n").join(lines)
        return Panel(content, title="System", border_style="dim", padding=(0, 1))

    def _build_progress_panel(self) -> Panel:
        """Build the pipeline progress panel."""
        tbl = Table.grid(padding=(0, 1))
        tbl.add_column()

        # Stage header
        stage_text = Text()
        stage_text.append(
            f"Stage {self._current_stage_idx}/{len(_STAGE_NAMES)} · ",
            style="dim",
        )
        stage_text.append(self._current_stage or "Starting", style="bold cyan")
        tbl.add_row(stage_text)
        tbl.add_row(Text())
        tbl.add_row(self._progress)

        return Panel(tbl, title="Pipeline", border_style="dim", padding=(0, 1))

    def _build_log_panel(self) -> Panel:
        """Build the log tail panel."""
        with self._log_lock:
            lines = list(self._log_lines)

        if not lines:
            content = Text("  Waiting for log output…", style="dim italic")
        else:
            parts = []
            for line in lines:
                t = Text(line)
                if " WARN" in line or " WARNING" in line:
                    t.stylize("yellow")
                elif " ERROR" in line or " CRITICAL" in line:
                    t.stylize("red bold")
                else:
                    t.stylize("dim")
                parts.append(t)
            content = Text("\n").join(parts)

        return Panel(content, title="Log", border_style="dim", padding=(0, 1))
