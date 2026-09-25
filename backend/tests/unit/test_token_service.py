from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, tzinfo
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
from src.services.token_service import _REUSE_GRACE_SECONDS, TokenService

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

    async def test_lost_rotation_race_issues_no_new_pair(self) -> None:
        # A concurrent refresh already revoked the session between our read and
        # our conditional revoke (revoke returns False): must not mint a pair.
        service, users, _, sessions = make_service()
        user = make_user()
        sessions.get_by_hash.return_value = make_session_row(user.id)
        users.get_by_id.return_value = user
        sessions.revoke.return_value = False
        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("raced")
        sessions.create.assert_not_awaited()

    async def test_reused_revoked_token_revokes_the_whole_family(self) -> None:
        """RFC 9700 / OAuth 2 BCP: replaying an already-rotated refresh token
        means the token leaked, so every session of that user dies -- otherwise
        the victim just re-logs-in and the thief keeps a live session."""
        service, users, _, sessions = make_service()
        user = make_user()
        rotated_at = datetime.now(UTC) - timedelta(seconds=_REUSE_GRACE_SECONDS + 1)
        # revoke() (rotation/logout) stamps both columns with the same instant.
        sessions.get_by_hash.return_value = make_session_row(
            user.id, revoked_at=rotated_at, last_used_at=rotated_at
        )
        users.get_by_id.return_value = user

        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("replayed")

        sessions.revoke_all_for_user.assert_awaited_once_with(user.id)
        sessions.create.assert_not_awaited()

    async def test_family_revoked_token_does_not_burn_the_family_again(self) -> None:
        """revoke_all_for_user (set-password, or a previous detection) leaves
        last_used_at NULL. A stale device presenting such a token an hour later
        was logged out, not robbed: it must not kill the session the user just
        created, e.g. on the phone they reset their password from."""
        service, users, _, sessions = make_service()
        user = make_user()
        sessions.get_by_hash.return_value = make_session_row(
            user.id, revoked_at=datetime.now(UTC) - timedelta(hours=1), last_used_at=None
        )
        users.get_by_id.return_value = user

        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("stale-laptop")

        sessions.revoke_all_for_user.assert_not_awaited()
        sessions.create.assert_not_awaited()

    @pytest.mark.parametrize(
        ("age", "burns"),
        [
            (timedelta(seconds=_REUSE_GRACE_SECONDS), False),
            (timedelta(seconds=_REUSE_GRACE_SECONDS, microseconds=1), True),
        ],
    )
    async def test_grace_window_boundary_is_inclusive(
        self, monkeypatch: pytest.MonkeyPatch, age: timedelta, burns: bool
    ) -> None:
        """Exactly _REUSE_GRACE_SECONDS old is still the benign race; one tick
        more is reuse. Frozen clock so the boundary is exact."""
        frozen = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz: tzinfo | None = None) -> _FrozenDatetime:
                return cls.fromtimestamp(frozen.timestamp(), tz)

        monkeypatch.setattr("src.services.token_service.datetime", _FrozenDatetime)
        service, users, _, sessions = make_service()
        user = make_user()
        revoked_at = frozen - age
        sessions.get_by_hash.return_value = make_session_row(
            user.id,
            revoked_at=revoked_at,
            last_used_at=revoked_at,
            expires_at=frozen + timedelta(days=1),
        )
        users.get_by_id.return_value = user

        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("boundary")

        assert sessions.revoke_all_for_user.await_count == (1 if burns else 0)

    async def test_reuse_inside_grace_window_does_not_revoke_the_family(self) -> None:
        """Two tabs share one refresh token in localStorage; when their access
        token expires together both POST it. The loser presents a token revoked
        a moment ago by the winner's rotation -- a benign race, not theft. It
        gets a plain 401 and the winner's fresh session survives."""
        service, users, _, sessions = make_service()
        user = make_user()
        sessions.get_by_hash.return_value = make_session_row(
            user.id, revoked_at=datetime.now(UTC) - timedelta(seconds=2)
        )
        users.get_by_id.return_value = user

        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("second-tab")

        sessions.revoke_all_for_user.assert_not_awaited()
        sessions.create.assert_not_awaited()

    async def test_never_rotated_token_still_rotates_normally(self) -> None:
        """The reuse branch must not touch a live token: it rotates as before
        and no family revocation happens."""
        service, users, _, sessions = make_service()
        user = make_user()
        row = make_session_row(user.id)
        sessions.get_by_hash.return_value = row
        users.get_by_id.return_value = user

        pair = await service.refresh_pair("fresh")

        sessions.revoke.assert_awaited_once_with(row)
        sessions.create.assert_awaited_once()
        assert hash_token(pair.refresh_token) == sessions.create.await_args.args[1]
        sessions.revoke_all_for_user.assert_not_awaited()

    async def test_unknown_token_does_not_revoke_anything(self) -> None:
        """An unknown hash proves nothing (typo, purged row) -- it must not be a
        remote kill switch for a user we cannot even identify."""
        service, _, _, sessions = make_service()
        sessions.get_by_hash.return_value = None

        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("garbage")

        sessions.revoke_all_for_user.assert_not_awaited()

    async def test_expired_token_does_not_revoke_the_family(self) -> None:
        """Expiry is the normal end of a 14-day session, not evidence of theft."""
        service, users, _, sessions = make_service()
        user = make_user()
        sessions.get_by_hash.return_value = make_session_row(
            user.id, expires_at=datetime.now(UTC) - timedelta(seconds=1)
        )
        users.get_by_id.return_value = user

        with pytest.raises(InvalidSessionError):
            await service.refresh_pair("stale")

        sessions.revoke_all_for_user.assert_not_awaited()


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

    async def test_lost_consume_race_not_found(self) -> None:
        # A concurrent redemption consumed the token between our peek and our
        # conditional consume (consume returns False): single-use holds.
        service, users, tokens, _ = make_service()
        user = make_user()
        tokens.get_by_hash.return_value = make_token_row(user.id)
        users.get_by_id.return_value = user
        tokens.consume.return_value = False
        with pytest.raises(TokenNotFoundError):
            await service.consume_action_token("raced")


class TestRevokeAllForUser:
    async def test_deletes_tokens_and_revokes_sessions(self) -> None:
        service, _, tokens, sessions = make_service()
        user_id = uuid.uuid4()
        await service.revoke_all_for_user(user_id)
        tokens.delete_unconsumed.assert_awaited_once_with(user_id)
        sessions.revoke_all_for_user.assert_awaited_once_with(user_id)
