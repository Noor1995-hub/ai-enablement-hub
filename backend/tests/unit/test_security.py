from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import SecretStr

from src.core.configs.auth import AuthSettings
from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)

AUTH = AuthSettings(jwt_secret=SecretStr("unit-test-secret-0123456789-0123456789"))


class TestPasswordHashing:
    def test_roundtrip(self) -> None:
        hashed = hash_password("s3cret-password")
        assert hashed != "s3cret-password"
        assert verify_password("s3cret-password", hashed)

    def test_wrong_password_fails(self) -> None:
        assert not verify_password("wrong", hash_password("right"))

    def test_malformed_hash_returns_false(self) -> None:
        assert not verify_password("anything", "not-a-bcrypt-hash")


class TestAccessToken:
    def test_roundtrip(self) -> None:
        user_id = uuid.uuid4()
        claims = decode_access_token(create_access_token(user_id, AUTH), AUTH)
        assert claims["sub"] == str(user_id)
        assert claims["typ"] == "access"
        assert claims["iss"] == AUTH.jwt_issuer
        assert claims["aud"] == AUTH.jwt_audience

    def test_expired_rejected(self) -> None:
        expired_auth = AUTH.model_copy(update={"access_token_minutes": -1})
        token = create_access_token(uuid.uuid4(), expired_auth)
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(token, AUTH)

    def test_wrong_secret_rejected(self) -> None:
        token = create_access_token(uuid.uuid4(), AUTH)
        other = AUTH.model_copy(
            update={"jwt_secret": SecretStr("other-secret-0123456789-0123456789")}
        )
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(token, other)

    def test_wrong_audience_rejected(self) -> None:
        other = AUTH.model_copy(update={"jwt_audience": "someone-else"})
        token = create_access_token(uuid.uuid4(), other)
        with pytest.raises(jwt.InvalidAudienceError):
            decode_access_token(token, AUTH)

    def test_wrong_issuer_rejected(self) -> None:
        other = AUTH.model_copy(update={"jwt_issuer": "someone-else"})
        token = create_access_token(uuid.uuid4(), other)
        with pytest.raises(jwt.InvalidIssuerError):
            decode_access_token(token, AUTH)

    def test_non_access_typ_rejected(self) -> None:
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "iat": now,
                "exp": now + timedelta(minutes=5),
                "iss": AUTH.jwt_issuer,
                "aud": AUTH.jwt_audience,
                "typ": "refresh",
            },
            AUTH.jwt_secret.get_secret_value(),
            algorithm="HS256",
        )
        with pytest.raises(jwt.InvalidTokenError, match="not an access token"):
            decode_access_token(token, AUTH)

    def test_missing_sub_rejected(self) -> None:
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "iat": now,
                "exp": now + timedelta(minutes=5),
                "iss": AUTH.jwt_issuer,
                "aud": AUTH.jwt_audience,
                "typ": "access",
            },
            AUTH.jwt_secret.get_secret_value(),
            algorithm="HS256",
        )
        with pytest.raises(jwt.MissingRequiredClaimError):
            decode_access_token(token, AUTH)


class TestOpaqueTokens:
    def test_unique_and_urlsafe(self) -> None:
        first, second = new_opaque_token(), new_opaque_token()
        assert first != second
        assert len(first) >= 40

    def test_hash_is_deterministic_sha256_hex(self) -> None:
        raw = new_opaque_token()
        assert hash_token(raw) == hash_token(raw)
        assert len(hash_token(raw)) == 64
        assert hash_token(raw) != hash_token(raw + "x")
