from __future__ import annotations

from src.core.configs.database import DatabaseSettings


def test_pool_recycle_defaults_to_thirty_minutes() -> None:
    """Azure PG closes idle connections; recycling before it does keeps
    pool_pre_ping from having to discover it the expensive way."""
    assert DatabaseSettings().pool_recycle_seconds == 1800


def test_pool_recycle_is_overridable() -> None:
    assert DatabaseSettings(pool_recycle_seconds=60).pool_recycle_seconds == 60
