"""Batch 3 cross-cutting concerns: token cleanup, rate limiting, CORS."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, Response

from src.core.configs.app import AppSettings
from src.core.dependencies.auth import get_token_service
from src.core.dependencies.database import get_session
from src.core.dependencies.domain import get_feedback_service
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.dependencies.settings import get_settings
from src.core.dependencies.user import get_user_service
from src.core.ratelimit import RateLimiter, rate_limiter
from src.core.security import hash_token, new_opaque_token
from src.db.models import AuthSession, AuthToken, User
from src.main import _run_daily_maintenance, app
from src.repositories.auth_session_repository import AuthSessionRepository
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.user_repository import UserRepository
from src.services.exceptions import InvalidCredentialsError, InvalidSessionError
from src.services.token_service import TokenPair, TokenService
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_user
from tests.fixtures.media import TEST_STORAGE

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

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

    async def test_daily_maintenance_purges_tokens_and_sweeps_the_limiter(
        self, engine: AsyncEngine, test_settings: Settings
    ) -> None:
        """The maintenance pass does two jobs now. The limiter half is asserted
        exactly; the DB half is asserted loosely on purpose — this function
        opens its OWN AsyncSession on the engine and commits outside the
        `db_session` fixture's rolled-back transaction, so it must not depend on
        rows another test planted. Row-level purge behaviour is pinned by
        test_purge_expired_removes_only_dead_rows above.
        """
        rate_limiter.is_limited("maintenance-probe")
        # Backdate the counter past its own window so the sweep is entitled to
        # collect it (the store holds monotonic timestamps).
        window_start, count, window_seconds = rate_limiter._store["maintenance-probe"]
        rate_limiter._store["maintenance-probe"] = (
            window_start - window_seconds - 1,
            count,
            window_seconds,
        )

        tokens, sessions, swept = await _run_daily_maintenance(engine, test_settings.auth)

        assert swept >= 1
        assert "maintenance-probe" not in rate_limiter._store
        assert tokens >= 0
        assert sessions >= 0


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
        # The real remaining window (the five bcrypt checks above took some of it).
        assert 0 < int(response.headers["Retry-After"]) <= 60

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

    async def test_keyed_on_the_hop_ingress_appends_not_the_forgeable_one(
        self, client: AsyncClient
    ) -> None:
        """The key is the rightmost X-Forwarded-For entry (the one ACA ingress
        appends): prepending a fresh fake address per call still shares one
        counter, while a genuinely different client gets its own."""

        async def attempt(forwarded_for: str) -> int:
            response = await client.post(
                "/api/auth/set-password",
                json={"token": "guess", "password": "whatever-pass-1"},
                headers={"X-Forwarded-For": forwarded_for},
            )
            return response.status_code

        for i in range(5):
            assert await attempt(f"203.0.113.{i}, 192.0.2.44") == 404
        assert await attempt("203.0.113.99, 192.0.2.44") == 429
        assert await attempt("192.0.2.45") == 404


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class _DeadSessionTokenService:
    """Every refresh token is dead: keeps 300 calls off the DB."""

    async def refresh_pair(self, raw_refresh: str) -> TokenPair:
        raise InvalidSessionError


_RIGHT_PASSWORD = "right-pass-1"


class _PasswordCheckUserService:
    """Only `_RIGHT_PASSWORD` authenticates, for any email: keeps 150+ logins free
    of bcrypt and the DB so the test exercises the router's counters alone."""

    def __init__(self, user: User) -> None:
        self._user = user

    async def authenticate(self, email: str, password: str) -> User:
        # Yield like the real one (DB lookup, then bcrypt in a thread pool), so
        # concurrent requests interleave here.
        await asyncio.sleep(0)
        if password != _RIGHT_PASSWORD:
            raise InvalidCredentialsError
        return self._user


class _StubPairTokenService:
    async def issue_pair(self, user: User) -> TokenPair:
        return TokenPair(access_token="a", refresh_token="r", expires_in=1800)


class TestLoginIpRateLimit:
    """Per-email keying alone lets one host try 5 passwords against every account
    for free. The per-IP counter bounds that spray, but it counts FAILED attempts
    only: a whole office logs in from one NAT IP, and a room of correct passwords
    must never lock itself out."""

    @pytest.fixture
    def clock(self, client: AsyncClient) -> _Clock:
        clock = _Clock()
        limiter = RateLimiter(clock=clock)
        user = User(email="whoever@example.com", role="user")
        app.dependency_overrides[get_rate_limiter] = lambda: limiter
        app.dependency_overrides[get_user_service] = lambda: _PasswordCheckUserService(user)
        app.dependency_overrides[get_token_service] = _StubPairTokenService
        return clock

    async def _login(
        self, client: AsyncClient, email: str, password: str, ip: str = "192.0.2.44"
    ) -> Response:
        return await client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            headers={"X-Forwarded-For": ip},
        )

    async def test_101st_attempt_after_100_failures_is_429_even_with_the_right_password(
        self, client: AsyncClient, clock: _Clock
    ) -> None:
        for i in range(100):
            response = await self._login(client, f"victim-{i}@example.com", "guess")
            assert response.status_code == 401
        clock.now += 100
        # A fresh email: its per-email counter is at zero, so only the per-IP
        # counter can produce this 429.
        response = await self._login(client, "fresh@example.com", _RIGHT_PASSWORD)
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "rate_limited"
        assert response.headers["Retry-After"] == "200"
        assert response.json()["error"]["message"] == "Too many attempts — try again in 4 minutes"

    async def test_successes_never_consume_the_per_ip_budget(
        self, client: AsyncClient, clock: _Clock
    ) -> None:
        for i in range(150):
            response = await self._login(client, f"learner-{i}@example.com", _RIGHT_PASSWORD)
            assert response.status_code == 200
        for i in range(99):
            response = await self._login(client, f"typo-{i}@example.com", "guess")
            assert response.status_code == 401
        response = await self._login(client, "last@example.com", _RIGHT_PASSWORD)
        assert response.status_code == 200

    async def test_concurrent_failures_cannot_exceed_the_cap(
        self, client: AsyncClient, clock: _Clock
    ) -> None:
        """A sprayer pipelines requests: every attempt is counted at entry, so
        120 in flight at once still get only 100 password checks."""
        responses = await asyncio.gather(
            *(self._login(client, f"victim-{i}@example.com", "guess") for i in range(120))
        )
        codes = [response.status_code for response in responses]
        assert codes.count(401) == 100
        assert codes.count(429) == 20

    async def test_a_success_refunds_its_attempt(self, client: AsyncClient, clock: _Clock) -> None:
        for i in range(99):
            assert (await self._login(client, f"typo-{i}@example.com", "guess")).status_code == 401
        for i in range(10):
            response = await self._login(client, f"learner-{i}@example.com", _RIGHT_PASSWORD)
            assert response.status_code == 200
        # Still one failure left in the budget: the successes gave theirs back.
        assert (await self._login(client, "typo-99@example.com", "guess")).status_code == 401
        assert (await self._login(client, "x@example.com", _RIGHT_PASSWORD)).status_code == 429

    async def test_a_per_email_429_does_not_charge_the_ip(
        self, client: AsyncClient, clock: _Clock
    ) -> None:
        """Refused by the per-email counter before any password check: that is
        not a failed guess, so the IP budget gets it back."""
        for _ in range(5):
            assert (await self._login(client, "one@example.com", "guess")).status_code == 401
        assert (await self._login(client, "one@example.com", "guess")).status_code == 429
        for i in range(95):
            assert (await self._login(client, f"v-{i}@example.com", "guess")).status_code == 401
        assert (await self._login(client, "x@example.com", _RIGHT_PASSWORD)).status_code == 429

    async def test_limit_is_per_client_ip(self, client: AsyncClient, clock: _Clock) -> None:
        for i in range(100):
            assert (
                await self._login(client, f"victim-{i}@example.com", "guess")
            ).status_code == 401
        response = await self._login(client, "fresh@example.com", _RIGHT_PASSWORD, ip="192.0.2.45")
        assert response.status_code == 200


class TestRefreshRateLimit:
    """Refresh is unauthenticated (the presented token IS the credential), so the
    only key is the client IP. A whole office sits behind one NAT IP and all its
    30-minute access tokens expire together after a workshop login, hence 300."""

    @pytest.fixture
    def clock(self, client: AsyncClient) -> _Clock:
        clock = _Clock()
        limiter = RateLimiter(clock=clock)
        app.dependency_overrides[get_rate_limiter] = lambda: limiter
        app.dependency_overrides[get_token_service] = _DeadSessionTokenService
        return clock

    async def _refresh(self, client: AsyncClient, ip: str = "192.0.2.44") -> Response:
        return await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "not-a-real-token"},
            headers={"X-Forwarded-For": ip},
        )

    async def test_301st_attempt_is_429_with_the_real_remaining_window(
        self, client: AsyncClient, clock: _Clock
    ) -> None:
        for _ in range(300):
            assert (await self._refresh(client)).status_code == 401
        clock.now += 100
        response = await self._refresh(client)
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "rate_limited"
        assert response.headers["Retry-After"] == "200"

    async def test_limit_is_per_client_ip(self, client: AsyncClient, clock: _Clock) -> None:
        for _ in range(300):
            assert (await self._refresh(client)).status_code == 401
        assert (await self._refresh(client)).status_code == 429
        assert (await self._refresh(client, ip="192.0.2.45")).status_code == 401


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


@pytest_asyncio.fixture
async def storage_client(
    db_session: AsyncSession, test_settings: Settings
) -> AsyncGenerator[AsyncClient]:
    """Same as conftest's `client` fixture, but with lesson-media storage
    configured — exercises the CSP builder's storage-aware branch (test_settings
    otherwise pins storage=None to stay hermetic). The CSP is computed fresh per
    request from `request.app.dependency_overrides`-aware settings resolution,
    so this override is enough; no app factory/reimport needed."""
    storage_settings = test_settings.model_copy(update={"storage": TEST_STORAGE})

    async def _override_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_settings] = lambda: storage_settings
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    try:
        yield client
    finally:
        await client.aclose()
        app.dependency_overrides.clear()


class TestContentSecurityPolicy:
    async def test_default_csp_has_frame_src_and_no_blob_endpoint(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/api/health")
        csp = response.headers["content-security-policy"]
        assert "img-src 'self' data:;" in csp
        assert "media-src 'self';" in csp
        assert (
            "frame-src https://www.youtube-nocookie.com https://player.vimeo.com "
            "https://*.sharepoint.com"
        ) in csp

    async def test_storage_configured_adds_blob_endpoint_to_img_and_media_src(
        self, storage_client: AsyncClient
    ) -> None:
        response = await storage_client.get("/api/health")
        csp = response.headers["content-security-policy"]
        assert f"img-src 'self' data: {TEST_STORAGE.blob_endpoint};" in csp
        assert f"media-src 'self' {TEST_STORAGE.blob_endpoint};" in csp

    async def test_csp_pins_base_uri_and_form_action(self, client: AsyncClient) -> None:
        """Neither directive falls back to default-src, so both must be explicit:
        base-uri stops an injected <base href> from re-pointing every relative
        URL, form-action stops a form POSTing credentials off-origin."""
        response = await client.get("/api/health")
        csp = response.headers["content-security-policy"]
        assert "base-uri 'self'" in csp
        assert "form-action 'self'" in csp

    async def test_docs_path_is_csp_exempt_in_dev_but_not_in_prod(
        self, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """The exemption exists only so dev's Swagger UI can load its CDN assets.
        In prod the docs routes do not exist at all, so nothing may be exempt --
        /docs falls through to the SPA catch-all and must carry the CSP."""

        async def _override_session() -> AsyncGenerator[AsyncSession]:
            yield db_session

        async def _csp_for(env: Literal["dev", "prod"]) -> str | None:
            settings = test_settings.model_copy(
                update={"app": AppSettings(url="https://hub.example.com", env=env)}
            )
            app.dependency_overrides[get_session] = _override_session
            app.dependency_overrides[get_settings] = lambda: settings
            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://testserver"
                ) as client:
                    response = await client.get("/docs")
                    return response.headers.get("content-security-policy")
            finally:
                app.dependency_overrides.clear()

        assert await _csp_for("dev") is None
        prod_csp = await _csp_for("prod")
        assert prod_csp is not None
        assert "script-src 'self'" in prod_csp


class TestUnhandledErrorEnvelope:
    """A bug no domain handler claims must still answer in the standard shape.

    `raise_app_exceptions=False` is required, not cosmetic: Starlette's
    ServerErrorMiddleware sends the 500 response and then re-raises so the ASGI
    server can log it, and httpx's ASGITransport surfaces that re-raise to the
    caller by default. Uvicorn swallows it after logging, so a real browser sees
    the JSON body this test asserts on.
    """

    async def test_unexpected_exception_returns_the_error_envelope(
        self, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        class _ExplodingFeedbackService:
            async def submit(self, *_args: object, **_kwargs: object) -> None:
                msg = "database went away"
                raise RuntimeError(msg)

        async def _override_session() -> AsyncGenerator[AsyncSession]:
            yield db_session

        user = await create_user(db_session, email="envelope-500@example.com")
        app.dependency_overrides[get_session] = _override_session
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_feedback_service] = _ExplodingFeedbackService
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        try:
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                response = await client.post(
                    "/api/feedback",
                    json={"lesson_id": str(uuid.uuid4()), "message": "boom"},
                    headers=auth_headers(user, test_settings),
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 500
        assert response.json() == {
            "error": {
                "code": "internal_error",
                "message": "Something went wrong. Please try again.",
            }
        }

    async def test_the_message_never_leaks_the_exception(
        self, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """The client gets a fixed sentence; the cause goes to the log only."""

        class _ExplodingFeedbackService:
            async def submit(self, *_args: object, **_kwargs: object) -> None:
                msg = "connection to db-secret-host:5432 failed"
                raise RuntimeError(msg)

        async def _override_session() -> AsyncGenerator[AsyncSession]:
            yield db_session

        user = await create_user(db_session, email="envelope-500b@example.com")
        app.dependency_overrides[get_session] = _override_session
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_feedback_service] = _ExplodingFeedbackService
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        try:
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                response = await client.post(
                    "/api/feedback",
                    json={"lesson_id": str(uuid.uuid4()), "message": "boom"},
                    headers=auth_headers(user, test_settings),
                )
        finally:
            app.dependency_overrides.clear()

        assert "db-secret-host" not in response.text
