from __future__ import annotations

import uuid

from sqlalchemy import select

from src.db.models import User
from src.repositories.base import AbstractUserRepository

__all__ = ["UserRepository"]


class UserRepository(AbstractUserRepository):
    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def set_password(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        user.password_set = True
        await self._session.commit()
        await self._session.refresh(user)
