from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.core.security import hash_password, verify_password
from src.services.exceptions import InvalidCredentialsError

if TYPE_CHECKING:
    from src.db.models import User
    from src.repositories.base import AbstractUserRepository

__all__ = ["UserService"]

# Verified against when the email is unknown or has no password, so that the
# request costs one bcrypt check either way (no timing oracle on email existence).
_DUMMY_HASH = "$2b$12$2bKOi32Xmh8ALpGC6mAXhePQxnIGkz8HyByXKDGbD79guq0aD8r4e"


class UserService:
    def __init__(self, repository: AbstractUserRepository) -> None:
        self._repository = repository

    async def authenticate(self, email: str, password: str) -> User:
        """Return the user for valid credentials; raise InvalidCredentialsError
        otherwise (unknown email, no password set, wrong password, inactive)."""
        user = await self._repository.get_by_email(email.strip().lower())
        if user is None or user.password_hash is None:
            verify_password(password, _DUMMY_HASH)
            raise InvalidCredentialsError
        if not verify_password(password, user.password_hash) or not user.is_active:
            raise InvalidCredentialsError
        return user

    async def set_password(self, user: User, password: str) -> None:
        await self._repository.set_password(user, hash_password(password))

    async def get_active_user(self, user_id: uuid.UUID) -> User | None:
        """User for a validated token subject; None if missing or deactivated."""
        user = await self._repository.get_by_id(user_id)
        if user is None or not user.is_active:
            return None
        return user
