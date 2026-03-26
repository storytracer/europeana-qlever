"""Tests for adaptive concurrency throttle."""

from __future__ import annotations

import threading
import time

import pytest

from europeana_qlever.monitor import ResourceSnapshot
from europeana_qlever.throttle import AdaptiveThrottle


def _snap(cpu: float = 50.0, mem: float = 50.0) -> ResourceSnapshot:
    """Create a ResourceSnapshot with given CPU and memory percentages.

    Sets ``process_cpu_pct`` equal to ``cpu`` (simulating our tool as the
    dominant CPU consumer) so the throttle reacts to process-level load.
    """
    return ResourceSnapshot(
        timestamp=time.time(),
        rss_mb=100,
        available_mb=50_000,
        total_mb=100_000,
        memory_pct=mem,
        disk_free_gb=500,
        disk_total_gb=1000,
        cpu_pct=cpu,
        swap_used_gb=0,
        swap_total_gb=8,
        process_cpu_pct=cpu,
        process_rss_mb=2000,
        child_count=10,
    )


class TestAcquireRelease:
    """Basic semaphore semantics."""

    def test_acquire_within_permits(self):
        t = AdaptiveThrottle(3)
        t.acquire()
        t.acquire()
        t.acquire()
        assert t.in_use == 3

    def test_acquire_blocks_when_exhausted(self):
        t = AdaptiveThrottle(1)
        t.acquire()

        acquired = threading.Event()

        def _worker():
            t.acquire()
            acquired.set()

        th = threading.Thread(target=_worker)
        th.start()

        # Should NOT acquire within 0.1s
        assert not acquired.wait(0.1)

        t.release()
        assert acquired.wait(1.0)
        assert t.in_use == 1
        t.release()
        th.join()

    def test_release_below_zero_clamps(self):
        t = AdaptiveThrottle(3)
        t.release()
        assert t.in_use == 0


class TestScaleDown:
    """Throttle reduces permits under pressure."""

    def test_scale_down_after_consecutive_high_cpu(self):
        t = AdaptiveThrottle(10, consecutive_samples=3, step_down=2)
        for _ in range(3):
            t.adjust(_snap(cpu=90))
        assert t.current_permits == 8

    def test_scale_down_after_consecutive_high_memory(self):
        t = AdaptiveThrottle(10, consecutive_samples=3, step_down=2, memory_target=80.0)
        for _ in range(3):
            t.adjust(_snap(cpu=50, mem=85))
        assert t.current_permits == 8

    def test_scale_down_respects_min(self):
        t = AdaptiveThrottle(4, min_permits=3, consecutive_samples=1, step_down=5)
        t.adjust(_snap(cpu=95))
        assert t.current_permits == 3

    def test_multiple_scale_downs(self):
        t = AdaptiveThrottle(10, consecutive_samples=2, step_down=2)
        # First scale-down
        for _ in range(2):
            t.adjust(_snap(cpu=90))
        assert t.current_permits == 8
        # Counter resets after acting — need 2 more samples
        for _ in range(2):
            t.adjust(_snap(cpu=90))
        assert t.current_permits == 6


class TestScaleUp:
    """Throttle increases permits when relaxed."""

    def test_scale_up_after_consecutive_low(self):
        t = AdaptiveThrottle(10, consecutive_samples=3, step_down=2, step_up=2)
        # Scale down first
        for _ in range(3):
            t.adjust(_snap(cpu=90))
        assert t.current_permits == 8
        # Scale up
        for _ in range(3):
            t.adjust(_snap(cpu=50))
        assert t.current_permits == 10

    def test_scale_up_respects_max(self):
        t = AdaptiveThrottle(5, consecutive_samples=1, step_up=2)
        # Already at max — no change
        t.adjust(_snap(cpu=50))
        assert t.current_permits == 5

    def test_scale_up_wakes_blocked_acquirers(self):
        t = AdaptiveThrottle(1, consecutive_samples=1, step_up=1, step_down=1)
        t.acquire()
        acquired = threading.Event()

        def _worker():
            t.acquire()
            acquired.set()

        th = threading.Thread(target=_worker)
        th.start()

        assert not acquired.wait(0.1)
        # Release to unblock
        t.release()
        assert acquired.wait(1.0)
        t.release()
        th.join()

    def test_max_permits_differs_from_initial(self):
        """Start at 5 permits but allow scaling up to 10."""
        t = AdaptiveThrottle(5, max_permits=10, consecutive_samples=1, step_up=2)
        assert t.current_permits == 5
        assert t.max_permits == 10
        # Scale up
        t.adjust(_snap(cpu=50))
        assert t.current_permits == 7
        t.adjust(_snap(cpu=50))
        assert t.current_permits == 9
        t.adjust(_snap(cpu=50))
        assert t.current_permits == 10  # capped at max
        t.adjust(_snap(cpu=50))
        assert t.current_permits == 10  # stays at max

    def test_start_half_scale_up_to_max(self):
        """Simulates the real scenario: start at workers//2, scale to workers."""
        workers = 20
        t = AdaptiveThrottle(
            workers // 2, max_permits=workers,
            consecutive_samples=3, step_up=2, step_down=2,
        )
        assert t.current_permits == 10
        # 3 low samples → scale up by 2
        for _ in range(3):
            t.adjust(_snap(cpu=40))
        assert t.current_permits == 12
        for _ in range(3):
            t.adjust(_snap(cpu=45))
        assert t.current_permits == 14
        # Now CPU rises into hysteresis band — no change
        for _ in range(3):
            t.adjust(_snap(cpu=75))
        assert t.current_permits == 14  # stable


class TestHysteresis:
    """No action in the dead zone between low and target."""

    def test_no_change_in_hysteresis_band(self):
        t = AdaptiveThrottle(
            10, cpu_target=85.0, cpu_low=65.0, consecutive_samples=1
        )
        # CPU at 75% — in the dead zone
        for _ in range(10):
            t.adjust(_snap(cpu=75))
        assert t.current_permits == 10

    def test_alternating_resets_counters(self):
        t = AdaptiveThrottle(10, consecutive_samples=3, step_down=2)
        # Two high, then one in dead zone — counter resets
        t.adjust(_snap(cpu=90))
        t.adjust(_snap(cpu=90))
        t.adjust(_snap(cpu=75))
        t.adjust(_snap(cpu=90))
        # Only 1 consecutive high, not 3 — no change
        assert t.current_permits == 10


class TestCallback:
    """on_adjust fires with correct arguments."""

    def test_callback_on_scale_down(self):
        calls = []
        t = AdaptiveThrottle(
            10, consecutive_samples=2, step_down=3,
            on_adjust=lambda c, m, r: calls.append((c, m, r)),
        )
        for _ in range(2):
            t.adjust(_snap(cpu=90))
        assert len(calls) == 1
        assert calls[0] == (7, 10, "scale down")

    def test_callback_on_scale_up(self):
        calls = []
        t = AdaptiveThrottle(
            10, consecutive_samples=1, step_down=2, step_up=2,
            on_adjust=lambda c, m, r: calls.append((c, m, r)),
        )
        t.adjust(_snap(cpu=95))  # scale down → 8
        t.adjust(_snap(cpu=50))  # scale up → 10
        assert calls[-1] == (10, 10, "scale up")

    def test_callback_exception_swallowed(self):
        def _bad_callback(c, m, r):
            raise RuntimeError("boom")

        t = AdaptiveThrottle(10, consecutive_samples=1, on_adjust=_bad_callback)
        # Should not raise
        t.adjust(_snap(cpu=95))
        assert t.current_permits == 8

    def test_callback_with_max_permits(self):
        """Callback reports max_permits, not initial_permits."""
        calls = []
        t = AdaptiveThrottle(
            5, max_permits=20, consecutive_samples=1, step_up=2,
            on_adjust=lambda c, m, r: calls.append((c, m, r)),
        )
        t.adjust(_snap(cpu=50))  # scale up → 7
        assert calls[0] == (7, 20, "scale up")


class TestConcurrency:
    """Thread-safety under concurrent acquire/release."""

    def test_concurrent_acquire_release(self):
        permits = 5
        t = AdaptiveThrottle(permits)
        max_concurrent = [0]
        current = [0]
        lock = threading.Lock()

        def _worker():
            for _ in range(10):
                t.acquire()
                with lock:
                    current[0] += 1
                    if current[0] > max_concurrent[0]:
                        max_concurrent[0] = current[0]
                time.sleep(0.001)
                with lock:
                    current[0] -= 1
                t.release()

        threads = [threading.Thread(target=_worker) for _ in range(10)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert max_concurrent[0] <= permits
        assert t.in_use == 0
