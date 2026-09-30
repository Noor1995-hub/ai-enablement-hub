from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, SecretStr, computed_field

__all__ = ["DatabaseProtocol", "DatabaseSettings"]


class DatabaseProtocol(StrEnum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class DatabaseSettings(BaseModel):
    """Database connection settings; env prefix `DATABASE__` (see Settings)."""

    model_config = ConfigDict(frozen=True)

    # Defaults to PostgreSQL (the only protocol this app runs on — asyncpg is a
    # main dep, dev/test/prod are all Azure PG). A missing DATABASE__ config
    # therefore fails loudly at URL resolution (password required) instead of
    # silently booting on a throwaway local SQLite file.
    protocol: DatabaseProtocol = DatabaseProtocol.POSTGRESQL
    host: str = ""
    port: int = 5432
    username: str = ""
    password: SecretStr = SecretStr("")
    name: str = "app.db"
    ssl_mode: str | None = None
    pool_size: int = 5
    max_overflow: int = 10
    # Azure Database for PostgreSQL closes idle server-side connections. Recycle
    # ours first: pool_pre_ping (set in main.py) already recovers from a killed
    # connection, but only after paying a failed round-trip to discover it.
    pool_recycle_seconds: int = 1800

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> SecretStr:
        if self.protocol is DatabaseProtocol.SQLITE:
            return SecretStr(f"sqlite+aiosqlite:///{self.name}")
        if not self.password.get_secret_value():
            msg = "DATABASE__PASSWORD is required for PostgreSQL"
            raise ValueError(msg)
        url = (
            f"postgresql+asyncpg://{self.username}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )
        if self.ssl_mode:
            url += f"?ssl={self.ssl_mode}"
        return SecretStr(url)
