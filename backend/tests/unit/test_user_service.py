from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.core.security import hash_password, verify_password
from src.db.models import User
from src.repositories.base import AbstractUserRepository
from src.services.exceptions import InvalidCredentialsError
from src.services.user_service import UserService

PASSWORD = "correct-horse-battery"
PASSWORD_HASH = hash_password(PASSWORD)


def make_user(**overrides: Any) -> User:
    fields: dict[str, Any] = {
        "id": uuid.uuid4(),
        "email": "user@example.com",
        "first_name": "Test",
        "last_name": "User",
        "role": "user",
        "is_active": True,
        "password_set": True,
        "password_hash": PASSWORD_HASH,
    }
    fields.update(overrides)
    return User(**fields)


def make_service(user: User | None) -> tuple[UserService, AsyncMock]:
    repository = AsyncMock(spec=AbstractUserRepository)
    repository.get_by_email.return_value = user
    repository.get_by_id.return_value = user
    return UserService(repository), repository


class TestAuthenticate:
    async def test_valid_credentials_returns_user(self) -> None:
        user = make_user()
        service, _ = make_service(user)
        assert await service.authenticate("user@example.com", PASSWORD) is user

    async def test_email_is_normalized_before_lookup(self) -> None:
        service, repository = make_service(make_user())
        await service.authenticate("  User@EXAMPLE.com ", PASSWORD)
        repository.get_by_email.assert_awaited_once_with("user@example.com")

    async def test_unknown_email_rejected(self) -> None:
        service, _ = make_service(None)
        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("nobody@example.com", PASSWORD)

    async def test_no_password_set_rejected(self) -> None:
        service, _ = make_service(make_user(password_hash=None, password_set=False))
        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("user@example.com", PASSWORD)

    async def test_wrong_password_rejected(self) -> None:
        service, _ = make_service(make_user())
        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("user@example.com", "wrong-password")

    async def test_inactive_user_rejected(self) -> None:
        service, _ = make_service(make_user(is_active=False))
        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("user@example.com", PASSWORD)


class TestSetPassword:
    async def test_stores_bcrypt_hash_of_password(self) -> None:
        user = make_user(password_hash=None, password_set=False)
        service, repository = make_service(user)
        await service.set_password(user, "new-password-123")
        repository.set_password.assert_awaited_once()
        passed_user, passed_hash = repository.set_password.await_args.args
        assert passed_user is user
        assert verify_password("new-password-123", passed_hash)


class TestGetActiveUser:
    async def test_returns_active_user(self) -> None:
        user = make_user()
        service, _ = make_service(user)
        assert await service.get_active_user(user.id) is user

    async def test_missing_user_returns_none(self) -> None:
        service, _ = make_service(None)
        assert await service.get_active_user(uuid.uuid4()) is None

    async def test_inactive_user_returns_none(self) -> None:
        user = make_user(is_active=False)
        service, _ = make_service(user)
        assert await service.get_active_user(user.id) is None
