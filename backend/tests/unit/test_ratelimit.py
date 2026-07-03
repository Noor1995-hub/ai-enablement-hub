from __future__ import annotations

from src.core.ratelimit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class TestRateLimiter:
    def test_allows_up_to_max_calls(self) -> None:
        limiter = RateLimiter(clock=FakeClock())
        assert all(not limiter.is_limited("k") for _ in range(5))

    def test_blocks_past_the_limit(self) -> None:
        limiter = RateLimiter(clock=FakeClock())
        for _ in range(5):
            limiter.is_limited("k")
        assert limiter.is_limited("k") is True

    def test_window_expiry_resets_the_counter(self) -> None:
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        for _ in range(6):
            limiter.is_limited("k")
        clock.now += 61
        assert limiter.is_limited("k") is False

    def test_blocked_attempts_do_not_slide_the_window(self) -> None:
        """JS-parity: the window is fixed from the first attempt; hammering
        while blocked doesn't extend it."""
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        for _ in range(6):
            limiter.is_limited("k")
        clock.now += 59  # still inside the original window
        assert limiter.is_limited("k") is True
        clock.now += 2  # first window (started at 1000.0) is now stale
        assert limiter.is_limited("k") is False

    def test_keys_are_independent(self) -> None:
        limiter = RateLimiter(clock=FakeClock())
        for _ in range(6):
            limiter.is_limited("a")
        assert limiter.is_limited("b") is False

    def test_custom_limits(self) -> None:
        limiter = RateLimiter(clock=FakeClock())
        assert limiter.is_limited("k", max_calls=1) is False
        assert limiter.is_limited("k", max_calls=1) is True

    def test_reset_clears_all_counters(self) -> None:
        limiter = RateLimiter(clock=FakeClock())
        for _ in range(6):
            limiter.is_limited("k")
        limiter.reset()
        assert limiter.is_limited("k") is False
