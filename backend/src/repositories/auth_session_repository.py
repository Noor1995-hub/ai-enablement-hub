from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import delete, func, or_, select, update

from src.db.models import AuthSession
from src.repositories.base import AbstractAuthSessionRepository

if TYPE_CHECKING:
    from sqlalchemy import CursorResult

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

    async def revoke(self, auth_session: AuthSession) -> bool:
        now = datetime.now(UTC)
        result = await self._session.execute(
            update(AuthSession)
            .where(AuthSession.id == auth_session.id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now, last_used_at=now)
        )
        await self._session.commit()
        revoked = cast("CursorResult[Any]", result).rowcount == 1
        if revoked:
            auth_session.revoked_at = now  # keep the passed ORM instance consistent
            auth_session.last_used_at = now
        return revoked

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.commit()

    async def last_used_by_user(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, datetime]:
        if not user_ids:
            return {}
        result = await self._session.execute(
            select(AuthSession.user_id, func.max(AuthSession.last_used_at))
            .where(AuthSession.user_id.in_(user_ids))
            .group_by(AuthSession.user_id)
        )
        # last_used_at is NULL until a session is first rotated/revoked, and
        # func.max skips NULLs — a user with only never-used sessions yields a
        # NULL max, which we drop so the key stays absent (= never active).
        return {user_id: last_used for user_id, last_used in result.all() if last_used is not None}

    async def delete_dead(self) -> int:
        result = await self._session.execute(
            delete(AuthSession).where(
                or_(
                    AuthSession.expires_at < datetime.now(UTC),
                    AuthSession.revoked_at.is_not(None),
                )
            )
        )
        await self._session.commit()
        return cast("CursorResult[Any]", result).rowcount
