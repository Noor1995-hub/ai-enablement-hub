from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.security import hash_password
from src.db.models import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["create_user"]


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password: str | None = None,
    role: str = "user",
    is_active: bool = True,
    first_name: str = "Test",
    last_name: str = "User",
) -> User:
    """Insert a user row; password=None mirrors a freshly-invited user."""
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=is_active,
        password_hash=hash_password(password) if password is not None else None,
        password_set=password is not None,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
