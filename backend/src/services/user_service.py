from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from fastapi.concurrency import run_in_threadpool

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
        # bcrypt is ~200-300ms of pure CPU; run it off the event loop so a login
        # never freezes the single-replica app for other requests (matches the
        # run_in_threadpool pattern used for ACS email and PyJWKClient).
        if user is None or user.password_hash is None:
            await run_in_threadpool(verify_password, password, _DUMMY_HASH)
            raise InvalidCredentialsError
        valid = await run_in_threadpool(verify_password, password, user.password_hash)
        if not valid or not user.is_active:
            raise InvalidCredentialsError
        return user

    async def set_password(self, user: User, password: str) -> None:
        password_hash = await run_in_threadpool(hash_password, password)
        await self._repository.set_password(user, password_hash)

    async def get_active_user(self, user_id: uuid.UUID) -> User | None:
        """User for a validated token subject; None if missing or deactivated."""
        user = await self._repository.get_by_id(user_id)
        if user is None or not user.is_active:
            return None
        return user
