"""Entra ID test doubles: a module-scope RSA keypair for minting RS256
id_tokens, a JWKS-provider stub, and a fake Microsoft token endpoint
(httpx.MockTransport) for the code-exchange leg."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr

from src.core.configs.entra import EntraSettings

__all__ = ["TEST_ENTRA", "FakeTokenEndpoint", "StubJWKS", "make_id_token", "other_key"]

TEST_ENTRA = EntraSettings(
    tenant_id="test-tenant",
    client_id="test-client-id",
    client_secret=SecretStr("test-client-secret"),
)

# Generated once per test process — key generation is the slow part.
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def other_key() -> rsa.RSAPrivateKey:
    """A keypair the StubJWKS does NOT vouch for (wrong-signature tests)."""
    return _OTHER_PRIVATE_KEY


def make_id_token(*, key: rsa.RSAPrivateKey | None = None, **overrides: Any) -> str:
    """Mint an RS256 id_token with valid-by-default claims; override any claim,
    or remove one by passing None."""
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": "pairwise-subject",
        "iss": TEST_ENTRA.issuer,
        "aud": TEST_ENTRA.client_id,
        "iat": now,
        "exp": now + timedelta(hours=1),
        "nonce": "test-nonce",
        "oid": "00000000-aaaa-bbbb-cccc-000000000001",
        "email": "user@delaware.pro",
        "preferred_username": "upn.fallback@delawareconsulting.com",
    }
    for claim, value in overrides.items():
        if value is None:
            claims.pop(claim, None)
        else:
            claims[claim] = value
    return jwt.encode(claims, key or _PRIVATE_KEY, algorithm="RS256", headers={"kid": "test-kid"})


class StubJWKS:
    """Stands in for PyJWKClient: always returns the test public key (the
    service unwraps PyJWK via getattr(key, "key", key), so a raw key works)."""

    def get_signing_key_from_jwt(self, token: str) -> rsa.RSAPublicKey:
        return _PRIVATE_KEY.public_key()


class FakeTokenEndpoint:
    """Microsoft's token endpoint as an httpx.MockTransport. Set `nonce` (and
    optionally `claims`) before the callback request; every exchange request
    is captured in `calls` for assertions."""

    def __init__(self) -> None:
        self.nonce = "test-nonce"
        self.claims: dict[str, Any] = {}
        self.status_code = 200
        self.calls: list[httpx.Request] = []

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self._handler))

    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if self.status_code != 200:
            return httpx.Response(self.status_code, json={"error": "invalid_grant"})
        id_token = make_id_token(nonce=self.nonce, **self.claims)
        return httpx.Response(200, json={"id_token": id_token, "token_type": "Bearer"})
