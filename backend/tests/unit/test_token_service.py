from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from src.core.configs.auth import AuthSettings
from src.core.security import decode_access_token, hash_token
from src.db.models import AuthSession, AuthToken, User
from src.repositories.base import (
    AbstractAuthSessionRepository,
    AbstractAuthTokenRepository,
    AbstractUserRepository,
)
from src.services.exceptions import (
    InvalidSessionError,
    TokenExpiredError,
    TokenNotFoundError,
)
from src.services.token_service import TokenService

AUTH = AuthSettings(jwt_secret=SecretStr("unit-test-secret-0123456789-0123456789"))


def make_user(**overrides: Any) -> User:
    fields: dict[str, Any] = {
        "id": uuid.uuid4(),
        "email": "user@example.com",
        "first_name": "Test",
        "last_name": "User",
        "role": "user",
        "is_active": True,
    }
    fields.update(overrides)
    return User(**fields)


def make_session_row(user_id: uuid.UUID, **overrides: Any) -> AuthSession:
    fields: dict[str, Any] = {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "token_hash": "irrelevant",
        "expires_at": datetime.now(UTC) + timedelta(days=14),
        "revoked_at": None,
    }
    fields.update(overrides)
    return AuthSession(**fields)


def make_token_row(user_id: uuid.UUID, **overrides: Any) -> AuthToken:
    fields: dict[str, Any] = {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "purpose": "invite",
        "token_hash": "irrelevant",
        "expires_at": datetime.now(UTC) + timedelta(days=7),
        "consumed_at": None,
    }
    fields.update(overrides)
    return AuthToken(**fields)


def make_service() -> tuple[TokenService, AsyncMock, AsyncMock, AsyncMock]:
    users = AsyncMock(spec=AbstractUserRepository)
    tokens = AsyncMock(spec=AbstractAuthTokenRepository)
    sessions = AsyncMock(spec=AbstractAuthSessionRepository)
    return TokenService(users, tokens, sessions, AUTH), users, tokens, sessions


class TestIssuePair:
    async def test_access_token_is_valid_and_refresh_is_stored_hashed(self) -> None:
        service, _, _, sessions = make_service()
        user = make_user()

        pair = await service.issue_pair(user)

        claims = decode_access_token(pair.access_token, AUTH)
        assert claims["sub"] == str(user.id)
        assert pair.expires_in == AUTH.access_token_minutes * 60
        sessions.create.assert_awaited_once()
        stored_user_id, stored_hash, expires_at = sessions.create.await_args.args
        assert stored_user_id == user.id
        assert stored_hash == hash_token(pair.refresh_token)
        expected = datetime.now(UTC) + timedelta(days=AUTH.refresh_token_days)
        assert abs((expires_at - expected).total_seconds()) < 30


class TestRefreshPair:
    async def test_rotation_revokes_old_and_issues_new(self) -> None:
        service, users, _, sessions = make_service()
        user = make_user()
        old_row = make_session_row(user.id)
        sessions.get_by_hash.return_value = old_row
        users.get_by_id.return_value = user

        pair = await service.refresh_pair("raw-refresh-token")

        sessions.get_by_hash.assert_awaited_once_with(hash_token("raw-refresh-token"))
        sessions.revoke.assert_awaited_once_with(old_row)
        sessions.create.assert_awaited_once()
        assert hash_token(pair.refresh_token) == sessions.create.await_args.args[1]

    async def test_unknown_token_rejected(self) -> None:
        service, _, _, sessions = make_service()
        sessions.get_by_hash.return_value = None
        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("unknown")

    async def test_revoked_session_rejected(self) -> None:
        service, _, _, sessions = make_service()
        user = make_user()
        sessions.get_by_hash.return_value = make_session_row(user.id, revoked_at=datetime.now(UTC))
        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("revoked")

    async def test_expired_session_rejected(self) -> None:
        service, _, _, sessions = make_service()
        user = make_user()
        sessions.get_by_hash.return_value = make_session_row(
            user.id, expires_at=datetime.now(UTC) - timedelta(seconds=1)
        )
        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("expired")

    async def test_missing_user_rejected(self) -> None:
        service, users, _, sessions = make_service()
        sessions.get_by_hash.return_value = make_session_row(uuid.uuid4())
        users.get_by_id.return_value = None
        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("orphaned")

    async def test_inactive_user_rejected(self) -> None:
        service, users, _, sessions = make_service()
        user = make_user(is_active=False)
        sessions.get_by_hash.return_value = make_session_row(user.id)
        users.get_by_id.return_value = user
        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("deactivated")


class TestRevokeSession:
    async def test_active_session_is_revoked(self) -> None:
        service, _, _, sessions = make_service()
        row = make_session_row(uuid.uuid4())
        sessions.get_by_hash.return_value = row
        await service.revoke_session("raw")
        sessions.revoke.assert_awaited_once_with(row)

    async def test_unknown_token_is_noop(self) -> None:
        service, _, _, sessions = make_service()
        sessions.get_by_hash.return_value = None
        await service.revoke_session("unknown")
        sessions.revoke.assert_not_awaited()

    async def test_already_revoked_is_noop(self) -> None:
        service, _, _, sessions = make_service()
        sessions.get_by_hash.return_value = make_session_row(
            uuid.uuid4(), revoked_at=datetime.now(UTC)
        )
        await service.revoke_session("revoked")
        sessions.revoke.assert_not_awaited()


class TestIssueActionToken:
    async def test_invite_stores_hash_with_invite_ttl(self) -> None:
        service, _, tokens, _ = make_service()
        user = make_user()

        raw = await service.issue_action_token(user, "invite")

        tokens.delete_unconsumed.assert_not_awaited()
        user_id, token_hash, purpose, expires_at = tokens.create.await_args.args
        assert (user_id, token_hash, purpose) == (user.id, hash_token(raw), "invite")
        expected = datetime.now(UTC) + timedelta(days=AUTH.invite_ttl_days)
        assert abs((expires_at - expected).total_seconds()) < 30

    async def test_reset_revokes_prior_reset_tokens(self) -> None:
        service, _, tokens, _ = make_service()
        user = make_user()

        await service.issue_action_token(user, "reset")

        tokens.delete_unconsumed.assert_awaited_once_with(user.id, purpose="reset")
        assert tokens.create.await_args.args[2] == "reset"


class TestPeekAndConsume:
    async def test_peek_returns_token_and_user(self) -> None:
        service, users, tokens, _ = make_service()
        user = make_user()
        row = make_token_row(user.id)
        tokens.get_by_hash.return_value = row
        users.get_by_id.return_value = user

        assert await service.peek_action_token("raw") == (row, user)
        tokens.consume.assert_not_awaited()

    async def test_unknown_token_not_found(self) -> None:
        service, _, tokens, _ = make_service()
        tokens.get_by_hash.return_value = None
        with pytest.raises(TokenNotFoundError):
            await service.peek_action_token("unknown")

    async def test_consumed_token_not_found(self) -> None:
        service, _, tokens, _ = make_service()
        tokens.get_by_hash.return_value = make_token_row(
            uuid.uuid4(), consumed_at=datetime.now(UTC)
        )
        with pytest.raises(TokenNotFoundError):
            await service.peek_action_token("used")

    async def test_expired_token_gone(self) -> None:
        service, _, tokens, _ = make_service()
        tokens.get_by_hash.return_value = make_token_row(
            uuid.uuid4(), expires_at=datetime.now(UTC) - timedelta(seconds=1)
        )
        with pytest.raises(TokenExpiredError):
            await service.peek_action_token("expired")

    async def test_inactive_user_not_found(self) -> None:
        service, users, tokens, _ = make_service()
        user = make_user(is_active=False)
        tokens.get_by_hash.return_value = make_token_row(user.id)
        users.get_by_id.return_value = user
        with pytest.raises(TokenNotFoundError):
            await service.peek_action_token("deactivated")

    async def test_consume_marks_token_used(self) -> None:
        service, users, tokens, _ = make_service()
        user = make_user()
        row = make_token_row(user.id)
        tokens.get_by_hash.return_value = row
        users.get_by_id.return_value = user

        assert await service.consume_action_token("raw") == (row, user)
        tokens.consume.assert_awaited_once_with(row)


class TestRevokeAllForUser:
    async def test_deletes_tokens_and_revokes_sessions(self) -> None:
        service, _, tokens, sessions = make_service()
        user_id = uuid.uuid4()
        await service.revoke_all_for_user(user_id)
        tokens.delete_unconsumed.assert_awaited_once_with(user_id)
        sessions.revoke_all_for_user.assert_awaited_once_with(user_id)
