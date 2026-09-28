"""In-process fixed-window rate limiter — port of the legacy rateLimit.js.

Same semantics as the original: one counter per key, window restarts when the
previous one is stale, attempts past the limit still count (a hammering client
never escapes the window). Honest limitation, unchanged from the JS version:
counters live in process memory, so they reset on restart and are per-replica.
Fine for a single local process / one Container Apps replica; move the
counters to a PG table if the app ever scales out.

The store is bounded two ways, because a dict keyed by client-supplied values
(an email, an X-Forwarded-For hop) is otherwise a memory leak with a public
trigger: `sweep()` drops counters whose OWN window can no longer affect a
decision (called daily from main.py's maintenance task), and `_MAX_KEYS` caps
the dict outright.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

__all__ = ["RateLimiter", "rate_limiter"]

logger = logging.getLogger(__name__)

# Hard ceiling on distinct keys (~100k entries is single-digit MB). Normal
# traffic is nowhere near it: keys are per-user or per-IP.
_MAX_KEYS = 100_000
# How many extra keys to reclaim once the ceiling is hit, so the eviction sort
# runs once per batch instead of once per request.
_EVICTION_BATCH = 1_000


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        # key -> (window_start, count, window_seconds). The window length
        # travels with the entry (not a single global constant) because
        # callers use very different windows for the same store — a 60s
        # login guard next to an 86400s chat-daily AI-spend counter — and both
        # sweeping and eviction need to know a key's OWN window to avoid
        # forgiving one that can still bite.
        self._store: dict[str, tuple[float, int, float]] = {}

    def is_limited(self, key: str, *, max_calls: int = 5, window_seconds: float = 60.0) -> bool:
        """Record one attempt for `key`; True when the attempt exceeds the limit."""
        now = self._clock()
        existing = self._store.get(key)
        if existing is None and len(self._store) >= _MAX_KEYS:
            self._make_room()
        if existing is not None:
            # The stored window wins over the one just passed, for as long as
            # the window is still live: a key's window is fixed for the life
            # of the counter, so a later call with a different window_seconds
            # for the same key must not silently change when it expires
            # mid-flight. The passed value only takes effect below when a new
            # window actually starts (fresh key, or the branch just below
            # where the stored window has elapsed).
            window_start, count, stored_window = existing
            if now - window_start > stored_window:
                window_start, count, stored_window = now, 0, window_seconds
        else:
            window_start, count, stored_window = now, 0, window_seconds
        count += 1
        self._store[key] = (window_start, count, stored_window)
        return count > max_calls

    def sweep(self, *, older_than: float | None = None) -> int:
        """Drop counters that can no longer affect a decision, return how many went.

        Default (`older_than=None`) is loss-free: a counter is only dropped
        once IT'S OWN window has elapsed, so it could only ever have answered
        False from here on. This is what main.py's daily maintenance task
        calls — a fixed-window store used by callers with very different
        window lengths (60s login guard vs. 86400s chat-daily) must not judge
        every key against the longest window in use, or short-window keys
        would sit in memory needlessly for up to a day.

        Passing `older_than` overrides the per-key window with one fixed
        cutoff for every entry instead — a coarser, caller-chosen bound. This
        is NOT loss-free in general (a fixed cutoff shorter than some key's own
        window can drop a counter that could still bite) — today it has no
        production caller, only a test exercises it. `_make_room` does NOT use
        this override; it needs the per-key behaviour (see there for the
        eviction path).
        """
        now = self._clock()
        stale = [
            key
            for key, (window_start, _count, window_seconds) in self._store.items()
            if now - window_start > (window_seconds if older_than is None else older_than)
        ]
        for key in stale:
            del self._store[key]
        return len(stale)

    def _make_room(self) -> None:
        """Reclaim space for a new key once `_MAX_KEYS` is reached.

        Two passes, cheapest and safest first:
          1. `sweep()` — already-expired counters (by their own window) go for
             free; this is most of the win under real traffic (many short-lived
             keys, e.g. rotating IPs).
          2. If the store isn't back down to at least `_EVICTION_BATCH` below
             the ceiling, evict the entries soonest to expire RELATIVE TO
             THEIR OWN WINDOW (`window_start + window_seconds` ascending) —
             not the oldest by creation time. Sorting by creation time alone
             would evict whichever counter happens to be oldest, which under a
             flood of fresh short-window keys is often a live long-window
             AI-spend counter (chat-daily, 86400s) that merely started
             earlier. Ranking by absolute expiry means a brand-new 60s key is
             evicted ahead of a chat-daily counter that still has hours left,
             so a key-flood effectively never uses up a learner's daily
             AI-spend allowance for free (the one edge: a chat-daily counter
             within its own last `_EVICTION_BATCH`-sized sliver of life can
             still be evicted a little early — harmless, since it was about to
             expire anyway). This DOES forgive some live short-window
             counters — that is the deliberate trade: an unbounded dict in a
             single-replica process is the worse failure. Reaching this branch
             means someone is manufacturing keys, so it logs; that log line is
             the signal to add a real store.

        Headroom, not just "back under the ceiling": requiring the store to
        land at `_MAX_KEYS - _EVICTION_BATCH` (not merely `< _MAX_KEYS`) is
        what makes the batch amortization in `_EVICTION_BATCH`'s own comment
        true. Without it, a store sitting exactly at the ceiling with only a
        trickle of expired keys per sweep (e.g. a sustained ~1.7k new 60s-window
        keys/second — enough to keep pace with 60s expiry at a 100k ceiling)
        would free one slot, immediately refill it on the next request, and
        pay the full O(n) sweep-and-maybe-sort again on every single request —
        exactly the per-request cost this batching exists to avoid.
        """
        self.sweep()
        if len(self._store) <= _MAX_KEYS - _EVICTION_BATCH:
            return
        overflow = len(self._store) - (_MAX_KEYS - _EVICTION_BATCH)
        doomed = sorted(self._store.items(), key=lambda item: item[1][0] + item[1][2])[:overflow]
        for key, _entry in doomed:
            del self._store[key]
        logger.warning(
            "rate-limiter store hit its %d-key ceiling; evicted %d live counter(s)",
            _MAX_KEYS,
            len(doomed),
        )

    def reset(self) -> None:
        """Clear all counters (tests)."""
        self._store.clear()


# Single shared instance; injected via core.dependencies.ratelimit.get_rate_limiter.
rate_limiter = RateLimiter()
