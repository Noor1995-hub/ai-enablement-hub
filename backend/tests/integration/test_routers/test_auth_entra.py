"""Entra ID sign-in endpoints (/api/auth/entra/*) against the real app with a
stubbed JWKS provider and a fake Microsoft token endpoint. Also carries the
purpose-confusion regressions: entra_login codes vs invite/reset tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, Response
from pydantic import SecretStr
from sqlalchemy import func, select

from src.core.configs.app import AppSettings
from src.core.configs.auth import AuthSettings
from src.core.configs.settings import Settings
from src.core.dependencies.database import get_session
from src.core.dependencies.entra import get_entra_service
from src.core.dependencies.settings import get_settings
from src.core.security import hash_token, new_opaque_token, pkce_challenge
from src.db.models import User
from src.main import app
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.user_repository import UserRepository
from src.services.entra_service import EntraService
from tests.fixtures.auth import bearer
from tests.fixtures.entra import TEST_ENTRA, FakeTokenEndpoint, StubJWKS
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.services.token_service import TokenService

_JWT_SECRET = SecretStr("integration-test-jwt-secret-0123456789")

# Explicit app/entra kwargs keep these hermetic even once the developer's
# backend/.env carries real ENTRA__* values.
ENTRA_ON = Settings(app=AppSettings(), auth=AuthSettings(jwt_secret=_JWT_SECRET), entra=TEST_ENTRA)
ENTRA_OFF = Settings(app=AppSettings(), auth=AuthSettings(jwt_secret=_JWT_SECRET), entra=None)

APP_URL = ENTRA_ON.app.url.rstrip("/")


@pytest.fixture
def token_endpoint() -> FakeTokenEndpoint:
    return FakeTokenEndpoint()


@pytest_asyncio.fixture
async def entra_client(
    db_session: AsyncSession, token_endpoint: FakeTokenEndpoint
) -> AsyncGenerator[AsyncClient]:
    """conftest's client with Entra configured and the service's outbound legs
    (JWKS, token endpoint) replaced by test doubles."""

    async def _override_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    http = token_endpoint.client()

    def _override_entra_service() -> EntraService:
        return EntraService(TEST_ENTRA, UserRepository(db_session), StubJWKS(), http=http)

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_settings] = lambda: ENTRA_ON
    app.dependency_overrides[get_entra_service] = _override_entra_service
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        await http.aclose()


@pytest_asyncio.fixture
async def off_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Entra explicitly unconfigured — the real get_entra_service runs."""

    async def _override_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_settings] = lambda: ENTRA_OFF
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


async def start_login(client: AsyncClient) -> tuple[str, str, str]:
    """GET /entra/login; returns (state, nonce, code_challenge) from the
    authorize URL. The state cookie lands in the client's jar automatically."""
    res = await client.get("/api/auth/entra/login")
    assert res.status_code == 302
    params = {k: v[0] for k, v in parse_qs(urlsplit(res.headers["location"]).query).items()}
    return params["state"], params["nonce"], params["code_challenge"]


def error_code(response: Response) -> str:
    location = response.headers["location"]
    assert location.startswith(f"{APP_URL}/login?error="), location
    return location.partition("error=")[2]


async def user_count(db_session: AsyncSession) -> int:
    return (await db_session.execute(select(func.count()).select_from(User))).scalar_one()


class TestAuthMethods:
    async def test_entra_on(self, entra_client: AsyncClient) -> None:
        res = await entra_client.get("/api/auth/methods")
        assert res.status_code == 200
        assert res.json() == {"password": True, "entra": True}

    async def test_entra_off(self, off_client: AsyncClient) -> None:
        res = await off_client.get("/api/auth/methods")
        assert res.status_code == 200
        assert res.json() == {"password": True, "entra": False}


class TestUnconfigured:
    async def test_endpoints_404_when_entra_disabled(self, off_client: AsyncClient) -> None:
        assert (await off_client.get("/api/auth/entra/login")).status_code == 404
        assert (await off_client.get("/api/auth/entra/callback")).status_code == 404
        assert (
            await off_client.post("/api/auth/entra/redeem", json={"code": "x"})
        ).status_code == 404


class TestEntraLogin:
    async def test_redirects_to_microsoft_with_state_cookie(
        self, entra_client: AsyncClient
    ) -> None:
        res = await entra_client.get("/api/auth/entra/login")
        assert res.status_code == 302
        location = res.headers["location"]
        assert location.startswith(
            f"https://login.microsoftonline.com/{TEST_ENTRA.tenant_id}/oauth2/v2.0/authorize?"
        )
        params = {k: v[0] for k, v in parse_qs(urlsplit(location).query).items()}
        assert params["redirect_uri"] == f"{APP_URL}/api/auth/entra/callback"
        assert params["code_challenge_method"] == "S256"

        set_cookie = res.headers["set-cookie"]
        assert "entra_oidc=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Path=/api/auth/entra" in set_cookie
        assert "Max-Age=600" in set_cookie
        assert "SameSite=lax" in set_cookie.lower() or "samesite=lax" in set_cookie.lower()
        # dev settings: the cookie must work on plain-http localhost.
        assert "Secure" not in set_cookie

    async def test_fresh_state_per_attempt(self, entra_client: AsyncClient) -> None:
        first = await start_login(entra_client)
        second = await start_login(entra_client)
        assert first[0] != second[0]
        assert first[1] != second[1]


class TestEntraCallback:
    async def test_full_flow_links_and_logs_in(
        self,
        entra_client: AsyncClient,
        token_endpoint: FakeTokenEndpoint,
        db_session: AsyncSession,
    ) -> None:
        user = await create_user(db_session, email="invitee@delaware.pro")
        assert user.password_set is False  # invited, never redeemed the link

        state, nonce, challenge = await start_login(entra_client)
        token_endpoint.nonce = nonce
        token_endpoint.claims = {"email": "invitee@delaware.pro"}

        res = await entra_client.get(f"/api/auth/entra/callback?code=auth-code&state={state}")
        assert res.status_code == 302
        location = res.headers["location"]
        assert location.startswith(f"{APP_URL}/auth/callback#code=")
        # The state cookie is consumed with the handshake.
        assert 'entra_oidc=""' in res.headers["set-cookie"]

        # The confidential exchange carried the verifier matching the challenge.
        form = {k: v[0] for k, v in parse_qs(token_endpoint.calls[0].content.decode()).items()}
        assert form["code"] == "auth-code"
        assert pkce_challenge(form["code_verifier"]) == challenge

        login_code = location.partition("#code=")[2]
        res = await entra_client.post("/api/auth/entra/redeem", json={"code": login_code})
        assert res.status_code == 200
        pair = res.json()
        assert pair["token_type"] == "bearer"

        me = await entra_client.get("/api/me", headers=bearer(pair["access_token"]))
        assert me.status_code == 200
        profile = me.json()
        assert profile["email"] == "invitee@delaware.pro"
        assert profile["external_login"] is True
        assert profile["password_set"] is False

        await db_session.refresh(user)
        assert user.external_id == "00000000-aaaa-bbbb-cccc-000000000001"

    async def test_second_login_uses_linked_oid(
        self,
        entra_client: AsyncClient,
        token_endpoint: FakeTokenEndpoint,
        db_session: AsyncSession,
    ) -> None:
        await create_user(db_session, email="linked@delaware.pro")

        for attempt_email in ("linked@delaware.pro", "renamed@delaware.pro"):
            state, nonce, _ = await start_login(entra_client)
            token_endpoint.nonce = nonce
            # Second round: email drift — the linked oid must still win.
            token_endpoint.claims = {"email": attempt_email}
            res = await entra_client.get(f"/api/auth/entra/callback?code=c&state={state}")
            assert res.status_code == 302
            assert "#code=" in res.headers["location"]

    async def test_user_cancelled_at_microsoft(self, entra_client: AsyncClient) -> None:
        state, _, _ = await start_login(entra_client)
        res = await entra_client.get(f"/api/auth/entra/callback?error=access_denied&state={state}")
        assert error_code(res) == "entra_denied"

    async def test_missing_cookie_is_invalid_state(self, entra_client: AsyncClient) -> None:
        # No prior /entra/login call — the jar has no state cookie.
        res = await entra_client.get("/api/auth/entra/callback?code=c&state=s")
        assert error_code(res) == "invalid_state"

    async def test_state_mismatch_rejected(self, entra_client: AsyncClient) -> None:
        await start_login(entra_client)
        res = await entra_client.get("/api/auth/entra/callback?code=c&state=tampered")
        assert error_code(res) == "invalid_state"

    async def test_garbage_cookie_rejected(self, entra_client: AsyncClient) -> None:
        entra_client.cookies.set(
            "entra_oidc", "not-a-jwt", domain="testserver", path="/api/auth/entra"
        )
        res = await entra_client.get("/api/auth/entra/callback?code=c&state=s")
        assert error_code(res) == "invalid_state"

    async def test_exchange_failure_is_entra_failed(
        self, entra_client: AsyncClient, token_endpoint: FakeTokenEndpoint
    ) -> None:
        state, _, _ = await start_login(entra_client)
        token_endpoint.status_code = 400
        res = await entra_client.get(f"/api/auth/entra/callback?code=bad&state={state}")
        assert error_code(res) == "entra_failed"

    async def test_wrong_nonce_is_entra_failed(
        self, entra_client: AsyncClient, token_endpoint: FakeTokenEndpoint
    ) -> None:
        state, _, _ = await start_login(entra_client)
        token_endpoint.nonce = "stale-nonce-from-another-handshake"
        res = await entra_client.get(f"/api/auth/entra/callback?code=c&state={state}")
        assert error_code(res) == "entra_failed"

    async def test_unknown_account_not_invited_and_not_provisioned(
        self,
        entra_client: AsyncClient,
        token_endpoint: FakeTokenEndpoint,
        db_session: AsyncSession,
    ) -> None:
        before = await user_count(db_session)
        state, nonce, _ = await start_login(entra_client)
        token_endpoint.nonce = nonce
        token_endpoint.claims = {"email": "stranger@delaware.pro"}
        res = await entra_client.get(f"/api/auth/entra/callback?code=c&state={state}")
        assert error_code(res) == "not_invited"
        assert await user_count(db_session) == before

    async def test_inactive_user_not_invited(
        self,
        entra_client: AsyncClient,
        token_endpoint: FakeTokenEndpoint,
        db_session: AsyncSession,
    ) -> None:
        await create_user(db_session, email="gone@delaware.pro", is_active=False)
        state, nonce, _ = await start_login(entra_client)
        token_endpoint.nonce = nonce
        token_endpoint.claims = {"email": "gone@delaware.pro"}
        res = await entra_client.get(f"/api/auth/entra/callback?code=c&state={state}")
        assert error_code(res) == "not_invited"

    async def test_rate_limited_after_ten_attempts(self, entra_client: AsyncClient) -> None:
        for _ in range(10):
            res = await entra_client.get("/api/auth/entra/callback?code=c&state=s")
            assert error_code(res) == "invalid_state"
        res = await entra_client.get("/api/auth/entra/callback?code=c&state=s")
        assert error_code(res) == "rate_limited"


class TestEntraRedeem:
    async def test_unknown_code_404(self, entra_client: AsyncClient) -> None:
        res = await entra_client.post("/api/auth/entra/redeem", json={"code": "unknown"})
        assert res.status_code == 404

    async def test_reuse_404(
        self,
        entra_client: AsyncClient,
        db_session: AsyncSession,
        token_service: TokenService,
    ) -> None:
        user = await create_user(db_session, email="reuse@delaware.pro")
        code = await token_service.issue_login_code(user)
        assert (
            await entra_client.post("/api/auth/entra/redeem", json={"code": code})
        ).status_code == 200
        assert (
            await entra_client.post("/api/auth/entra/redeem", json={"code": code})
        ).status_code == 404

    async def test_expired_code_410(
        self, entra_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await create_user(db_session, email="slow@delaware.pro")
        raw = new_opaque_token()
        # Direct row with past expiry — issue_login_code has no expiry knob.
        await AuthTokenRepository(db_session).create(
            user.id,
            hash_token(raw),
            "entra_login",
            datetime.now(UTC) - timedelta(seconds=1),
        )
        res = await entra_client.post("/api/auth/entra/redeem", json={"code": raw})
        assert res.status_code == 410

    async def test_rate_limited_429(self, entra_client: AsyncClient) -> None:
        for _ in range(5):
            await entra_client.post("/api/auth/entra/redeem", json={"code": "x"})
        res = await entra_client.post("/api/auth/entra/redeem", json={"code": "x"})
        assert res.status_code == 429


class TestPurposeConfusion:
    """A leaked login code must be worthless everywhere but /entra/redeem,
    and invite/reset links must be worthless at /entra/redeem."""

    async def test_login_code_rejected_by_set_password(
        self,
        entra_client: AsyncClient,
        db_session: AsyncSession,
        token_service: TokenService,
    ) -> None:
        user = await create_user(db_session, email="victim@delaware.pro")
        code = await token_service.issue_login_code(user)
        res = await entra_client.post(
            "/api/auth/set-password", json={"token": code, "password": "attacker-pw-123"}
        )
        assert res.status_code == 404

    async def test_login_code_rejected_by_invite_info(
        self,
        entra_client: AsyncClient,
        db_session: AsyncSession,
        token_service: TokenService,
    ) -> None:
        user = await create_user(db_session, email="peek@delaware.pro")
        code = await token_service.issue_login_code(user)
        res = await entra_client.get(f"/api/auth/invite/{code}")
        assert res.status_code == 404

    async def test_invite_token_rejected_by_redeem(
        self,
        entra_client: AsyncClient,
        db_session: AsyncSession,
        token_service: TokenService,
    ) -> None:
        user = await create_user(db_session, email="invited@delaware.pro")
        invite = await token_service.issue_action_token(user, "invite")
        res = await entra_client.post("/api/auth/entra/redeem", json={"code": invite})
        assert res.status_code == 404
        # The invite link keeps working afterwards (nothing was consumed).
        assert (await entra_client.get(f"/api/auth/invite/{invite}")).status_code == 200
