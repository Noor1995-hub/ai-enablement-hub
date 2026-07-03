from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.configs.database import DatabaseSettings

__all__ = ["Settings"]


class Settings(BaseSettings):
    database: DatabaseSettings = DatabaseSettings()

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )
