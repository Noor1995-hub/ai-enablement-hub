from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import delete, select, update

from src.db.models import AuthToken
from src.repositories.base import AbstractAuthTokenRepository

if TYPE_CHECKING:
    from sqlalchemy import CursorResult

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

    async def consume(self, token: AuthToken) -> bool:
        now = datetime.now(UTC)
        result = await self._session.execute(
            update(AuthToken)
            .where(AuthToken.id == token.id, AuthToken.consumed_at.is_(None))
            .values(consumed_at=now)
        )
        await self._session.commit()
        consumed = cast("CursorResult[Any]", result).rowcount == 1
        if consumed:
            token.consumed_at = now  # keep the passed ORM instance consistent
        return consumed

    async def delete_unconsumed(self, user_id: uuid.UUID, purpose: str | None = None) -> None:
        stmt = delete(AuthToken).where(
            AuthToken.user_id == user_id, AuthToken.consumed_at.is_(None)
        )
        if purpose is not None:
            stmt = stmt.where(AuthToken.purpose == purpose)
        await self._session.execute(stmt)
        await self._session.commit()

    async def delete_expired(self) -> int:
        result = await self._session.execute(
            delete(AuthToken).where(AuthToken.expires_at < datetime.now(UTC))
        )
        await self._session.commit()
        return cast("CursorResult[Any]", result).rowcount
