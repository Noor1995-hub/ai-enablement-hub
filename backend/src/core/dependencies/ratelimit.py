from __future__ import annotations

from src.core.ratelimit import RateLimiter, rate_limiter

__all__ = ["get_rate_limiter"]


def get_rate_limiter() -> RateLimiter:
    return rate_limiter
