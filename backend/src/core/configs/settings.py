from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.configs.app import AppSettings
from src.core.configs.auth import AuthSettings
from src.core.configs.database import DatabaseSettings
from src.core.configs.email import EmailSettings
from src.core.configs.entra import EntraSettings

__all__ = ["Settings"]


class Settings(BaseSettings):
    app: AppSettings = AppSettings()
    database: DatabaseSettings = DatabaseSettings()
    # No default: AUTH__JWT_SECRET must be set or startup fails loudly.
    auth: AuthSettings
    # None = Entra ID login disabled (endpoints 404, login button hidden).
    entra: EntraSettings | None = None
    # None = invite/reset emails disabled (admin shares links manually).
    email: EmailSettings | None = None

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )
