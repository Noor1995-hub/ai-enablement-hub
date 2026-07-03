from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select

from src.db.models import AuthToken
from src.repositories.base import AbstractAuthTokenRepository

__all__ = ["AuthTokenRepository"]


class AuthTokenRepository(AbstractAuthTokenRepository):
    async def create(
        self, user_id: uuid.UUID, token_hash: str, purpose: str, expires_at: datetime
    ) -> AuthToken:
        token = AuthToken(
            user_id=user_id, token_hash=token_hash, purpose=purpose, expires_at=expires_at
        )
        self._session.add(token)
        await self._session.commit()
        await self._session.refresh(token)
        return token

    async def get_by_hash(self, token_hash: str) -> AuthToken | None:
        result = await self._session.execute(
            select(AuthToken).where(AuthToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def consume(self, token: AuthToken) -> None:
        token.consumed_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(token)

    async def delete_unconsumed(self, user_id: uuid.UUID, purpose: str | None = None) -> None:
        stmt = delete(AuthToken).where(
            AuthToken.user_id == user_id, AuthToken.consumed_at.is_(None)
        )
        if purpose is not None:
            stmt = stmt.where(AuthToken.purpose == purpose)
        await self._session.execute(stmt)
        await self._session.commit()
