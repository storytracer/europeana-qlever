"""Adaptive concurrency throttle based on CPU and memory pressure.

Replaces a fixed ``threading.Semaphore`` with a dynamic permit system that
scales concurrency up or down in response to real-time resource utilisation.

The throttle is driven by :class:`~europeana_qlever.monitor.ResourceMonitor`
snapshots — call :meth:`adjust` on each sample to evaluate pressure and
update the permit count.  Workers use :meth:`acquire` / :meth:`release`
exactly like a ``threading.Semaphore``.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from .monitor import ResourceSnapshot

logger = logging.getLogger(__name__)


class AdaptiveThrottle:
    """Dynamic semaphore that adjusts permits based on system load.

    Parameters
    ----------
    initial_permits : int
        Starting permit count.
    max_permits : int or None
        Ceiling — never exceed this. Defaults to *initial_permits*.
    min_permits : int
        Floor — never go below this.
    cpu_target : float
        CPU % above which we scale down.
    cpu_low : float
        CPU % below which we scale up (hysteresis).
    memory_target : float
        Memory % above which we scale down.
    memory_low : float
        Memory % below which we scale up (hysteresis).
    consecutive_samples : int
        Required consecutive samples above/below threshold before acting.
    step_down : int
        Permits removed per scale-down event.
    step_up : int
        Permits added per scale-up event.
    on_adjust : callable or None
        ``(current_permits, max_permits, reason)`` callback on each adjustment.
    """

    def __init__(
        self,
        initial_permits: int,
        *,
        max_permits: int | None = None,
        min_permits: int = 2,
        cpu_target: float = 85.0,
        cpu_low: float = 65.0,
        memory_target: float = 85.0,
        memory_low: float = 70.0,
        consecutive_samples: int = 3,
        step_down: int = 2,
        step_up: int = 1,
        on_adjust: Callable[[int, int, str], None] | None = None,
    ) -> None:
        self._max = max_permits if max_permits is not None else initial_permits
        self._min = max(1, min_permits)
        self._cpu_target = cpu_target
        self._cpu_low = cpu_low
        self._mem_target = memory_target
        self._mem_low = memory_low
        self._consecutive = max(1, consecutive_samples)
        self._step_down = max(1, step_down)
        self._step_up = max(1, step_up)
        self._on_adjust = on_adjust

        self._permits = initial_permits
        self._in_use = 0
        self._cond = threading.Condition(threading.Lock())

        # Consecutive-sample counters
        self._high_count = 0
        self._low_count = 0

    # -- Semaphore interface -----------------------------------------------

    def acquire(self) -> None:
        """Block until a permit is available, then acquire it."""
        with self._cond:
            while self._in_use >= self._permits:
                self._cond.wait()
            self._in_use += 1

    def release(self) -> None:
        """Return a permit and wake one blocked acquirer."""
        with self._cond:
            self._in_use = max(0, self._in_use - 1)
            self._cond.notify()

    # -- Adaptive control --------------------------------------------------

    def adjust(self, snap: ResourceSnapshot) -> None:
        """Evaluate a resource snapshot and adjust permits if warranted.

        Called once per monitor sample (typically every 1 s during active work).
        """
        cpu = snap.process_cpu_pct if hasattr(snap, "process_cpu_pct") else snap.cpu_pct
        pressure = cpu > self._cpu_target or snap.memory_pct > self._mem_target
        relaxed = cpu < self._cpu_low and snap.memory_pct < self._mem_low

        if pressure:
            self._high_count += 1
            self._low_count = 0
        elif relaxed:
            self._low_count += 1
            self._high_count = 0
        else:
            # In hysteresis band — reset both counters, do nothing
            self._high_count = 0
            self._low_count = 0

        with self._cond:
            if self._high_count >= self._consecutive and self._permits > self._min:
                old = self._permits
                self._permits = max(self._min, self._permits - self._step_down)
                self._high_count = 0
                self._notify_adjust(old, "scale down", snap)

            elif self._low_count >= self._consecutive and self._permits < self._max:
                old = self._permits
                self._permits = min(self._max, self._permits + self._step_up)
                self._low_count = 0
                # Wake blocked acquirers since we have more permits now
                self._cond.notify(self._step_up)
                self._notify_adjust(old, "scale up", snap)

    def _notify_adjust(
        self, old_permits: int, reason: str, snap: ResourceSnapshot
    ) -> None:
        """Log and fire callback on adjustment (must hold _cond lock)."""
        cpu = snap.process_cpu_pct if hasattr(snap, "process_cpu_pct") else snap.cpu_pct
        logger.info(
            "Throttle %s: permits %d → %d (CPU=%.0f%%, MEM=%.0f%%)",
            reason,
            old_permits,
            self._permits,
            cpu,
            snap.memory_pct,
        )
        if self._on_adjust is not None:
            try:
                self._on_adjust(self._permits, self._max, reason)
            except Exception:
                pass

    # -- Properties --------------------------------------------------------

    @property
    def current_permits(self) -> int:
        """Current permit count (may differ from initial if adjusted)."""
        return self._permits

    @property
    def max_permits(self) -> int:
        """Maximum permit count (the initial value)."""
        return self._max

    @property
    def in_use(self) -> int:
        """Number of permits currently held."""
        return self._in_use
