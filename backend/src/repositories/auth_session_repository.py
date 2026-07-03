from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update

from src.db.models import AuthSession
from src.repositories.base import AbstractAuthSessionRepository

__all__ = ["AuthSessionRepository"]


class AuthSessionRepository(AbstractAuthSessionRepository):
    async def create(
        self, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> AuthSession:
        auth_session = AuthSession(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(auth_session)
        await self._session.commit()
        await self._session.refresh(auth_session)
        return auth_session

    async def get_by_hash(self, token_hash: str) -> AuthSession | None:
        result = await self._session.execute(
            select(AuthSession).where(AuthSession.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, auth_session: AuthSession) -> None:
        now = datetime.now(UTC)
        auth_session.revoked_at = now
        auth_session.last_used_at = now
        await self._session.commit()
        await self._session.refresh(auth_session)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.commit()
