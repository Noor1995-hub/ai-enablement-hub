from __future__ import annotations

from functools import lru_cache

from src.core.configs.settings import Settings

__all__ = ["get_settings"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
