"""In-process fixed-window rate limiter — port of the legacy rateLimit.js.

Same semantics as the original: one counter per key, window restarts when the
previous one is stale, attempts past the limit still count (a hammering client
never escapes the window). Honest limitation, unchanged from the JS version:
counters live in process memory, so they reset on restart and are per-replica.
Fine for a single local process / one Container Apps replica; move the
counters to a PG table if the app ever scales out.
"""

from __future__ import annotations

import time
from collections.abc import Callable

__all__ = ["RateLimiter", "rate_limiter"]


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._store: dict[str, tuple[float, int]] = {}

    def is_limited(self, key: str, *, max_calls: int = 5, window_seconds: float = 60.0) -> bool:
        """Record one attempt for `key`; True when the attempt exceeds the limit."""
        now = self._clock()
        window_start, count = self._store.get(key, (now, 0))
        if now - window_start > window_seconds:
            window_start, count = now, 0
        count += 1
        self._store[key] = (window_start, count)
        return count > max_calls

    def reset(self) -> None:
        """Clear all counters (tests)."""
        self._store.clear()


# Single shared instance; injected via core.dependencies.ratelimit.get_rate_limiter.
rate_limiter = RateLimiter()
