from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest

from src.core.security import pkce_challenge
from src.db.models import User
from src.repositories.base import AbstractUserRepository
from src.services.entra_service import EntraService
from src.services.exceptions import EntraExchangeError, EntraUserNotFoundError
from tests.fixtures.entra import TEST_ENTRA, StubJWKS, make_id_token, other_key

REDIRECT_URI = "http://localhost:5173/api/auth/entra/callback"


def make_user(**overrides: Any) -> User:
    fields: dict[str, Any] = {
        "id": uuid.uuid4(),
        "email": "user@delaware.pro",
        "first_name": "Test",
        "last_name": "User",
        "role": "user",
        "is_active": True,
        "external_id": None,
    }
    fields.update(overrides)
    return User(**fields)


def make_service(
    handler: Any | None = None,
) -> tuple[EntraService, AsyncMock]:
    users = AsyncMock(spec=AbstractUserRepository)
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler)) if handler else None
    return EntraService(TEST_ENTRA, users, StubJWKS(), http=http), users


class TestBuildAuthorizeUrl:
    def test_all_oauth_params_present(self) -> None:
        service, _ = make_service()
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        url = service.build_authorize_url(
            state="state-1",
            nonce="nonce-1",
            code_challenge=pkce_challenge(verifier),
            redirect_uri=REDIRECT_URI,
        )
        base, _, _ = url.partition("?")
        assert (
            base
            == f"https://login.microsoftonline.com/{TEST_ENTRA.tenant_id}/oauth2/v2.0/authorize"
        )
        params = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        assert params == {
            "client_id": TEST_ENTRA.client_id,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "response_mode": "query",
            "scope": "openid profile email",
            "state": "state-1",
            "nonce": "nonce-1",
            "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }


class TestExchangeCode:
    async def test_success_returns_id_token_and_sends_confidential_form(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"id_token": "the-id-token"})

        service, _ = make_service(handler)
        id_token = await service.exchange_code(
            code="auth-code", code_verifier="verifier-1", redirect_uri=REDIRECT_URI
        )

        assert id_token == "the-id-token"
        assert captured[0].url == TEST_ENTRA.token_url
        form = {k: v[0] for k, v in parse_qs(captured[0].content.decode()).items()}
        assert form == {
            "grant_type": "authorization_code",
            "client_id": TEST_ENTRA.client_id,
            "client_secret": "test-client-secret",
            "code": "auth-code",
            "redirect_uri": REDIRECT_URI,
            "code_verifier": "verifier-1",
        }

    async def test_non_200_rejected(self) -> None:
        service, _ = make_service(lambda _: httpx.Response(400, json={"error": "invalid_grant"}))
        with pytest.raises(EntraExchangeError):
            await service.exchange_code(code="c", code_verifier="v", redirect_uri=REDIRECT_URI)

    async def test_missing_id_token_rejected(self) -> None:
        service, _ = make_service(lambda _: httpx.Response(200, json={"access_token": "only"}))
        with pytest.raises(EntraExchangeError):
            await service.exchange_code(code="c", code_verifier="v", redirect_uri=REDIRECT_URI)

    async def test_non_json_rejected(self) -> None:
        service, _ = make_service(lambda _: httpx.Response(200, text="<html>oops</html>"))
        with pytest.raises(EntraExchangeError):
            await service.exchange_code(code="c", code_verifier="v", redirect_uri=REDIRECT_URI)

    async def test_network_error_rejected(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        service, _ = make_service(handler)
        with pytest.raises(EntraExchangeError):
            await service.exchange_code(code="c", code_verifier="v", redirect_uri=REDIRECT_URI)


class TestValidateIdToken:
    async def test_valid_token_returns_claims(self) -> None:
        service, _ = make_service()
        claims = await service.validate_id_token(make_id_token(), nonce="test-nonce")
        assert claims["oid"] == "00000000-aaaa-bbbb-cccc-000000000001"
        assert claims["email"] == "user@delaware.pro"

    async def test_wrong_issuer_rejected(self) -> None:
        service, _ = make_service()
        token = make_id_token(iss="https://login.microsoftonline.com/other-tenant/v2.0")
        with pytest.raises(EntraExchangeError):
            await service.validate_id_token(token, nonce="test-nonce")

    async def test_wrong_audience_rejected(self) -> None:
        service, _ = make_service()
        with pytest.raises(EntraExchangeError):
            await service.validate_id_token(make_id_token(aud="someone-else"), nonce="test-nonce")

    async def test_expired_beyond_leeway_rejected(self) -> None:
        service, _ = make_service()
        token = make_id_token(exp=datetime.now(UTC) - timedelta(hours=2))
        with pytest.raises(EntraExchangeError):
            await service.validate_id_token(token, nonce="test-nonce")

    async def test_wrong_nonce_rejected(self) -> None:
        service, _ = make_service()
        with pytest.raises(EntraExchangeError):
            await service.validate_id_token(make_id_token(), nonce="different-nonce")

    async def test_wrong_signing_key_rejected(self) -> None:
        service, _ = make_service()
        with pytest.raises(EntraExchangeError):
            await service.validate_id_token(make_id_token(key=other_key()), nonce="test-nonce")

    async def test_hs256_alg_confusion_rejected(self) -> None:
        """A symmetric token must never satisfy the RS256-only decoder."""
        service, _ = make_service()
        now = datetime.now(UTC)
        forged = jwt.encode(
            {
                "sub": "s",
                "iss": TEST_ENTRA.issuer,
                "aud": TEST_ENTRA.client_id,
                "iat": now,
                "exp": now + timedelta(hours=1),
                "nonce": "test-nonce",
                "oid": "forged-oid",
            },
            "guessable-shared-secret-padded-to-32-bytes!",
            algorithm="HS256",
        )
        with pytest.raises(EntraExchangeError):
            await service.validate_id_token(forged, nonce="test-nonce")

    async def test_missing_oid_rejected(self) -> None:
        service, _ = make_service()
        with pytest.raises(EntraExchangeError):
            await service.validate_id_token(make_id_token(oid=None), nonce="test-nonce")


class TestResolveUser:
    OID = "00000000-aaaa-bbbb-cccc-000000000001"

    def claims(self, **overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "oid": self.OID,
            "email": "user@delaware.pro",
            "preferred_username": "upn.fallback@delawareconsulting.com",
        }
        for claim, value in overrides.items():
            if value is None:
                base.pop(claim, None)
            else:
                base[claim] = value
        return base

    async def test_linked_oid_logs_in(self) -> None:
        service, users = make_service()
        user = make_user(external_id=self.OID)
        users.get_by_external_id.return_value = user

        assert await service.resolve_user(self.claims()) is user
        users.get_by_email.assert_not_awaited()
        users.link_external_id.assert_not_awaited()

    async def test_linked_oid_with_changed_email_still_logs_in(self) -> None:
        service, users = make_service()
        user = make_user(external_id=self.OID, email="old-name@delaware.pro")
        users.get_by_external_id.return_value = user

        assert await service.resolve_user(self.claims()) is user

    async def test_linked_but_inactive_rejected(self) -> None:
        service, users = make_service()
        users.get_by_external_id.return_value = make_user(external_id=self.OID, is_active=False)
        with pytest.raises(EntraUserNotFoundError):
            await service.resolve_user(self.claims())

    async def test_first_login_links_by_email(self) -> None:
        service, users = make_service()
        user = make_user()
        users.get_by_external_id.return_value = None
        users.get_by_email.return_value = user

        assert await service.resolve_user(self.claims()) is user
        users.get_by_email.assert_awaited_once_with("user@delaware.pro")
        users.link_external_id.assert_awaited_once_with(user, self.OID)

    async def test_email_claim_normalized(self) -> None:
        service, users = make_service()
        users.get_by_external_id.return_value = None
        users.get_by_email.return_value = make_user()

        await service.resolve_user(self.claims(email="  User@Delaware.PRO "))
        users.get_by_email.assert_awaited_once_with("user@delaware.pro")

    async def test_missing_email_falls_back_to_preferred_username(self) -> None:
        service, users = make_service()
        users.get_by_external_id.return_value = None
        users.get_by_email.return_value = make_user(email="upn.fallback@delawareconsulting.com")

        await service.resolve_user(self.claims(email=None))
        users.get_by_email.assert_awaited_once_with("upn.fallback@delawareconsulting.com")

    async def test_no_email_claims_at_all_rejected(self) -> None:
        service, users = make_service()
        users.get_by_external_id.return_value = None
        with pytest.raises(EntraUserNotFoundError):
            await service.resolve_user(self.claims(email=None, preferred_username=None))
        users.get_by_email.assert_not_awaited()

    async def test_unknown_user_rejected_and_never_provisioned(self) -> None:
        service, users = make_service()
        users.get_by_external_id.return_value = None
        users.get_by_email.return_value = None
        with pytest.raises(EntraUserNotFoundError):
            await service.resolve_user(self.claims())
        users.link_external_id.assert_not_awaited()

    async def test_inactive_email_match_rejected(self) -> None:
        service, users = make_service()
        users.get_by_external_id.return_value = None
        users.get_by_email.return_value = make_user(is_active=False)
        with pytest.raises(EntraUserNotFoundError):
            await service.resolve_user(self.claims())
        users.link_external_id.assert_not_awaited()

    async def test_email_match_already_linked_to_other_oid_rejected(self) -> None:
        """Same email, different oid: never relink silently."""
        service, users = make_service()
        users.get_by_external_id.return_value = None
        users.get_by_email.return_value = make_user(external_id="some-other-oid")
        with pytest.raises(EntraUserNotFoundError):
            await service.resolve_user(self.claims())
        users.link_external_id.assert_not_awaited()


class TestLogHygiene:
    """Review item 9.12: these records go to Log Analytics, whose retention and
    access are separate from the database's. The oid is the opaque identifier the
    flow is debugged from and stays; no email address may appear."""

    OID = "0000-oid-1234"
    ADDRESSES = ("sarah.jones@example.com", "old.sarah@example.com", "sarah.jones")

    def _rendered(self, caplog: pytest.LogCaptureFixture) -> str:
        return "\n".join(record.getMessage() for record in caplog.records)

    def _assert_clean(self, caplog: pytest.LogCaptureFixture) -> str:
        rendered = self._rendered(caplog)
        assert rendered
        for fragment in self.ADDRESSES:
            assert fragment not in rendered
        return rendered

    async def test_rejected_signin_logs_the_oid_and_domain_not_the_email(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        service, users = make_service()
        users.get_by_external_id.return_value = None
        users.get_by_email.return_value = None
        claims = {"oid": self.OID, "email": "sarah.jones@example.com"}

        with (
            caplog.at_level(logging.WARNING, logger="src.services.entra_service"),
            pytest.raises(EntraUserNotFoundError),
        ):
            await service.resolve_user(claims)

        rendered = self._assert_clean(caplog)
        assert self.OID in rendered
        assert "example.com" in rendered

    async def test_a_claim_without_an_at_sign_does_not_leak_through_the_domain(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        service, users = make_service()
        users.get_by_external_id.return_value = None
        users.get_by_email.return_value = None
        claims = {"oid": self.OID, "preferred_username": "sarah.jones"}

        with (
            caplog.at_level(logging.WARNING, logger="src.services.entra_service"),
            pytest.raises(EntraUserNotFoundError),
        ):
            await service.resolve_user(claims)

        self._assert_clean(caplog)

    async def test_email_drift_logs_no_address(self, caplog: pytest.LogCaptureFixture) -> None:
        service, users = make_service()
        users.get_by_external_id.return_value = make_user(
            external_id=self.OID, email="old.sarah@example.com"
        )
        claims = {"oid": self.OID, "email": "sarah.jones@example.com"}

        with caplog.at_level(logging.INFO, logger="src.services.entra_service"):
            await service.resolve_user(claims)

        assert self.OID in self._assert_clean(caplog)

    async def test_conflicting_oid_logs_no_address(self, caplog: pytest.LogCaptureFixture) -> None:
        service, users = make_service()
        users.get_by_external_id.return_value = None
        users.get_by_email.return_value = make_user(
            external_id="some-other-oid", email="sarah.jones@example.com"
        )
        claims = {"oid": self.OID, "email": "sarah.jones@example.com"}

        with (
            caplog.at_level(logging.ERROR, logger="src.services.entra_service"),
            pytest.raises(EntraUserNotFoundError),
        ):
            await service.resolve_user(claims)

        rendered = self._assert_clean(caplog)
        assert self.OID in rendered
        assert "some-other-oid" in rendered

    async def test_first_login_link_logs_no_address(self, caplog: pytest.LogCaptureFixture) -> None:
        service, users = make_service()
        users.get_by_external_id.return_value = None
        users.get_by_email.return_value = make_user(email="sarah.jones@example.com")
        claims = {"oid": self.OID, "email": "sarah.jones@example.com"}

        with caplog.at_level(logging.INFO, logger="src.services.entra_service"):
            await service.resolve_user(claims)

        assert self.OID in self._assert_clean(caplog)
