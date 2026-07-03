"""Batch 3 cross-cutting concerns: token cleanup, rate limiting, CORS."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from src.core.security import hash_token, new_opaque_token
from src.db.models import AuthSession, AuthToken
from src.repositories.auth_session_repository import AuthSessionRepository
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.user_repository import UserRepository
from src.services.token_service import TokenService
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


class TestTokenCleanup:
    async def test_purge_expired_removes_only_dead_rows(
        self, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="cleanup@example.com")
        now = datetime.now(UTC)

        def token_row(expires_delta: timedelta) -> AuthToken:
            return AuthToken(
                user_id=user.id,
                purpose="invite",
                token_hash=hash_token(new_opaque_token()),
                expires_at=now + expires_delta,
            )

        def session_row(expires_delta: timedelta, revoked: bool = False) -> AuthSession:
            return AuthSession(
                user_id=user.id,
                token_hash=hash_token(new_opaque_token()),
                expires_at=now + expires_delta,
                revoked_at=now if revoked else None,
            )

        live_token = token_row(timedelta(days=1))
        live_session = session_row(timedelta(days=1))
        db_session.add_all(
            [
                token_row(timedelta(days=-1)),  # expired token
                live_token,
                session_row(timedelta(days=-1)),  # expired session
                session_row(timedelta(days=1), revoked=True),  # revoked session
                live_session,
            ]
        )
        await db_session.commit()

        service = TokenService(
            UserRepository(db_session),
            AuthTokenRepository(db_session),
            AuthSessionRepository(db_session),
            test_settings.auth,
        )
        tokens_deleted, sessions_deleted = await service.purge_expired()
        assert (tokens_deleted, sessions_deleted) == (1, 2)

        assert await AuthTokenRepository(db_session).get_by_hash(live_token.token_hash)
        assert await AuthSessionRepository(db_session).get_by_hash(live_session.token_hash)


class TestLoginRateLimit:
    async def test_sixth_attempt_is_429_even_with_correct_password(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await create_user(db_session, email="bruteforced@example.com", password="right-pass-1")
        for _ in range(5):
            response = await client.post(
                "/api/auth/login",
                json={"email": "bruteforced@example.com", "password": "wrong"},
            )
            assert response.status_code == 401
        response = await client.post(
            "/api/auth/login",
            json={"email": "bruteforced@example.com", "password": "right-pass-1"},
        )
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "rate_limited"
        assert response.headers["Retry-After"] == "60"

    async def test_limit_is_per_email(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await create_user(db_session, email="innocent@example.com", password="my-own-pass-1")
        for _ in range(6):
            await client.post(
                "/api/auth/login", json={"email": "victim@example.com", "password": "x"}
            )
        response = await client.post(
            "/api/auth/login", json={"email": "innocent@example.com", "password": "my-own-pass-1"}
        )
        assert response.status_code == 200


class TestSetPasswordRateLimit:
    async def test_sixth_attempt_is_429(self, client: AsyncClient) -> None:
        """Keyed by client IP (all httpx test requests share one)."""
        for _ in range(5):
            response = await client.post(
                "/api/auth/set-password",
                json={"token": "guess", "password": "whatever-pass-1"},
            )
            assert response.status_code == 404
        response = await client.post(
            "/api/auth/set-password", json={"token": "guess", "password": "whatever-pass-1"}
        )
        assert response.status_code == 429


class TestCors:
    async def test_preflight_allows_the_dev_frontend_origin(self, client: AsyncClient) -> None:
        response = await client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "POST" in response.headers["access-control-allow-methods"]
        assert response.headers["access-control-max-age"] == "86400"

    async def test_unknown_origin_gets_no_cors_headers(self, client: AsyncClient) -> None:
        response = await client.options(
            "/api/auth/login",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "access-control-allow-origin" not in response.headers
