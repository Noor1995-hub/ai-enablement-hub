from __future__ import annotations

import logging

import pytest

from src.core import ratelimit
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

    def test_a_live_key_keeps_its_stored_window_despite_a_different_argument(self) -> None:
        """A key's window is fixed for the life of its counter. A later call
        for the SAME key with a different window_seconds must not reshape a
        still-live window -- only a fresh key or an actually-expired window
        may adopt the newly passed value."""
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        limiter.is_limited("k", window_seconds=60)
        clock.now += 10  # still well inside the original 60s window
        limiter.is_limited("k", window_seconds=5)  # a different window, same live key

        # The stored window (60) wins, not the 5 just passed.
        assert limiter._store["k"] == (1000.0, 2, 60.0)

        clock.now += 45  # 55s after the window started: past a 5s window, still inside 60s
        limiter.is_limited("k", window_seconds=5)
        # Still the original window -- if 5 had won on the earlier call, this
        # would already have reset (window_start would have moved to 1055).
        assert limiter._store["k"][0] == 1000.0


class TestRetryAfter:
    def test_counts_down_the_real_remaining_window(self) -> None:
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        limiter.is_limited("k", window_seconds=300)
        clock.now += 100.4
        assert limiter.retry_after("k", window_seconds=300) == 200

    def test_is_the_full_window_at_first_and_never_zero(self) -> None:
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        limiter.is_limited("k", window_seconds=60)
        assert limiter.retry_after("k", window_seconds=60) == 60
        clock.now += 60
        assert limiter.retry_after("k", window_seconds=60) == 1

    def test_unknown_or_stale_key_is_a_full_window(self) -> None:
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        assert limiter.retry_after("never-seen", window_seconds=60) == 60
        limiter.is_limited("k", window_seconds=60)
        clock.now += 61
        assert limiter.retry_after("k", window_seconds=60) == 60


class TestRefund:
    """Reserve-then-refund lets a caller count only some outcomes (failed
    logins) while still counting every attempt at entry, so concurrent
    requests can't all slip under the limit."""

    def test_charge_reports_the_window_it_counted_against(self) -> None:
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        assert limiter.charge("k", max_calls=1) == (False, 1000.0)
        clock.now += 10
        assert limiter.charge("k", max_calls=1) == (True, 1000.0)
        clock.now += 61
        assert limiter.charge("k", max_calls=1) == (False, 1071.0)

    def test_gives_back_one_attempt(self) -> None:
        limiter = RateLimiter(clock=FakeClock())
        for _ in range(4):
            limiter.is_limited("k")
        _, window_start = limiter.charge("k")
        limiter.refund("k", window_start=window_start)
        assert limiter.is_limited("k") is False
        assert limiter.is_limited("k") is True

    def test_never_goes_below_zero(self) -> None:
        limiter = RateLimiter(clock=FakeClock())
        _, window_start = limiter.charge("k", max_calls=1)
        limiter.refund("k", window_start=window_start)
        limiter.refund("k", window_start=window_start)
        assert limiter.is_limited("k", max_calls=1) is False
        assert limiter.is_limited("k", max_calls=1) is True

    def test_absent_key_is_a_no_op(self) -> None:
        limiter = RateLimiter(clock=FakeClock())
        limiter.refund("never-seen", window_start=1000.0)
        assert limiter.is_limited("never-seen", max_calls=1) is False
        assert limiter.is_limited("never-seen", max_calls=1) is True

    def test_refund_after_a_rollover_leaves_the_new_window_alone(self) -> None:
        """The charge was made in window A; while its request was in flight the
        window expired and a later request opened window B. The refund belongs
        to A, so B's count must not move."""
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        _, charged_in = limiter.charge("k", window_seconds=60)
        clock.now += 61
        limiter.is_limited("k", window_seconds=60)  # rolls over into window B
        limiter.refund("k", window_start=charged_in)
        assert limiter._store["k"] == (1061.0, 1, 60)


class TestSweep:
    """`sweep` is what keeps the process-global store from growing forever.
    It must be loss-free: a counter is only droppable once its window can no
    longer affect a decision."""

    def test_sweep_drops_a_counter_once_its_own_window_elapses(self) -> None:
        """Per-key windows, not one global cutoff: a plain 60s-window key is
        droppable after 61s, long before a 24h chat-daily counter would be."""
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        limiter.is_limited("stale-key")  # default 60s window
        clock.now += 61

        assert limiter.sweep() == 1

    def test_sweep_keeps_a_counter_that_can_still_bite(self) -> None:
        """A chat-daily counter is 24h wide; sweeping it early would hand back
        an AI-spend allowance the caller already used up."""
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        for _ in range(200):
            limiter.is_limited("chat-daily:u1", max_calls=200, window_seconds=86_400)
        clock.now += 3_600  # an hour later, still inside the daily window

        assert limiter.sweep() == 0
        assert limiter.is_limited("chat-daily:u1", max_calls=200, window_seconds=86_400) is True

    def test_a_swept_key_starts_from_zero(self) -> None:
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        for _ in range(6):
            limiter.is_limited("k")
        clock.now += 86_401
        limiter.sweep()

        assert limiter.is_limited("k") is False

    def test_sweep_honours_an_explicit_window(self) -> None:
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        limiter.is_limited("k")
        clock.now += 120

        assert limiter.sweep(older_than=60) == 1


class TestCapacityCeiling:
    """The store is a plain dict in a single-replica process. A flood of unique
    keys (spoofed X-Forwarded-For, enumerated emails) is the only realistic way
    to grow it, and an unbounded dict is a worse failure than a reset counter.

    `limiter._store` is read directly below. That is deliberate: the ceiling is
    an internal-memory invariant with no public read, and inventing a
    `__len__`/accessor just for the test would be worse.
    """

    def test_new_keys_cannot_grow_the_store_without_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ratelimit, "_MAX_KEYS", 10)
        monkeypatch.setattr(ratelimit, "_EVICTION_BATCH", 2)
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        for i in range(50):
            clock.now += 1  # distinct window starts, so "oldest" is well-defined
            limiter.is_limited(f"flood-{i}")

        assert len(limiter._store) <= 10

    def test_stale_counters_are_evicted_before_live_ones(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ratelimit, "_MAX_KEYS", 3)
        monkeypatch.setattr(ratelimit, "_EVICTION_BATCH", 1)
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        limiter.is_limited("ancient")
        clock.now += 86_401
        limiter.is_limited("live-a")
        limiter.is_limited("live-b")
        limiter.is_limited("live-c")  # trips the ceiling; "ancient" is the free win

        assert "ancient" not in limiter._store
        assert {"live-a", "live-b", "live-c"} <= set(limiter._store)

    def test_evicting_a_live_counter_is_logged(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Reaching this branch means someone is manufacturing keys — it must
        leave a signal, not silently forgive them."""
        monkeypatch.setattr(ratelimit, "_MAX_KEYS", 2)
        monkeypatch.setattr(ratelimit, "_EVICTION_BATCH", 1)
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        with caplog.at_level(logging.WARNING, logger="src.core.ratelimit"):
            for i in range(5):
                clock.now += 1
                limiter.is_limited(f"k{i}")

        assert any("ceiling" in record.message for record in caplog.records)

    def test_a_flood_of_short_window_keys_does_not_evict_a_live_chat_daily_counter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ruling (review 2.6/7.3 follow-up): eviction must never free
        AI-spend counters first. A naive "oldest window_start first" policy
        would pick the chat-daily counter here, because it was created before
        the flood — even though it still has almost a full day left on its
        window. Ranking by each key's OWN expiry (window_start +
        window_seconds) protects it: the flood's 60s keys expire in minutes,
        long before the daily counter does.
        """
        monkeypatch.setattr(ratelimit, "_MAX_KEYS", 5)
        monkeypatch.setattr(ratelimit, "_EVICTION_BATCH", 1)
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        limiter.is_limited("chat-daily:victim", max_calls=200, window_seconds=86_400)
        for i in range(10):
            clock.now += 1  # distinct, short-lived window starts
            limiter.is_limited(f"flood-{i}", max_calls=5, window_seconds=60)

        assert "chat-daily:victim" in limiter._store
        # Untouched by the flood: still its original window and count, not reset.
        assert limiter._store["chat-daily:victim"] == (1000.0, 1, 86_400)

    def test_make_room_leaves_batch_headroom_so_the_next_keys_skip_the_scan(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Review Important-1: `_make_room` must land the store at
        `_MAX_KEYS - _EVICTION_BATCH`, not merely back under `_MAX_KEYS`.
        Otherwise, near the ceiling with only a trickle of expiring keys, one
        freed slot is immediately refilled by the next request, which pays
        another full store scan — the exact per-request O(n) cost
        `_EVICTION_BATCH`'s own comment says batching avoids. This counts
        `_make_room` invocations directly (via monkeypatch) rather than
        inferring them from store size, since a same-sized store before and
        after is not proof that no scan ran.
        """
        monkeypatch.setattr(ratelimit, "_MAX_KEYS", 10)
        monkeypatch.setattr(ratelimit, "_EVICTION_BATCH", 3)
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        for i in range(10):
            clock.now += 1
            limiter.is_limited(f"live-{i}")  # fills to the ceiling; none expire on their own

        calls = 0
        original_make_room = limiter._make_room

        def counting_make_room() -> None:
            nonlocal calls
            calls += 1
            original_make_room()

        monkeypatch.setattr(limiter, "_make_room", counting_make_room)

        clock.now += 1
        limiter.is_limited("trigger")  # trips the ceiling: exactly one make-room pass
        assert calls == 1
        assert len(limiter._store) == ratelimit._MAX_KEYS - ratelimit._EVICTION_BATCH + 1

        for i in range(ratelimit._EVICTION_BATCH - 1):
            clock.now += 1
            limiter.is_limited(f"after-{i}")

        assert calls == 1  # the batch headroom absorbed these without another scan


class TestRefundAndRetryAfterOnTheBoundedStore:
    """Both read the key's OWN stored window, like is_limited() and sweep()."""

    def test_refund_never_creates_a_key(self) -> None:
        """A refund for an unknown key must not add an entry: that would be a
        way to grow the store without passing is_limited()'s ceiling check."""
        limiter = RateLimiter(clock=FakeClock())
        limiter.refund("never-seen", window_start=1000.0)
        assert "never-seen" not in limiter._store

    def test_refund_keeps_the_stored_window(self) -> None:
        limiter = RateLimiter(clock=FakeClock())
        _, window_start = limiter.charge("k", window_seconds=86_400)
        limiter.refund("k", window_start=window_start)
        assert limiter._store["k"] == (1000.0, 0, 86_400)

    def test_retry_after_uses_the_stored_window(self) -> None:
        clock = FakeClock()
        limiter = RateLimiter(clock=clock)
        limiter.is_limited("k", window_seconds=300)
        clock.now += 100
        assert limiter.retry_after("k", window_seconds=60) == 200
