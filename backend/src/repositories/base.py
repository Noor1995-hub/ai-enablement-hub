from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.db.models import AuthSession, AuthToken, User

__all__ = [
    "AbstractAuthSessionRepository",
    "AbstractAuthTokenRepository",
    "AbstractUserRepository",
]


class AbstractUserRepository(ABC):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def set_password(self, user: User, password_hash: str) -> None:
        """Persist a new password hash and mark password_set=true."""


class AbstractAuthTokenRepository(ABC):
    """Single-use invite/reset tokens (auth_tokens)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def create(
        self, user_id: uuid.UUID, token_hash: str, purpose: str, expires_at: datetime
    ) -> AuthToken: ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> AuthToken | None: ...

    @abstractmethod
    async def consume(self, token: AuthToken) -> None:
        """Mark the token used (consumed_at = now)."""

    @abstractmethod
    async def delete_unconsumed(self, user_id: uuid.UUID, purpose: str | None = None) -> None:
        """Revoke a user's outstanding tokens by deleting them (all purposes if None)."""


class AbstractAuthSessionRepository(ABC):
    """Refresh-token sessions (auth_sessions)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @abstractmethod
    async def create(
        self, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> AuthSession: ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> AuthSession | None: ...

    @abstractmethod
    async def revoke(self, auth_session: AuthSession) -> None:
        """Set revoked_at (and last_used_at) = now."""

    @abstractmethod
    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None: ...
