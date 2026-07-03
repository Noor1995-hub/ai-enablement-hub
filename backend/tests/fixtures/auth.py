from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.security import create_access_token

if TYPE_CHECKING:
    from src.core.configs.settings import Settings
    from src.db.models import User

__all__ = ["auth_headers", "bearer"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def auth_headers(user: User, settings: Settings) -> dict[str, str]:
    return bearer(create_access_token(user.id, settings.auth))
