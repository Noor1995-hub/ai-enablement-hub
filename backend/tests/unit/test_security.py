from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import pytest
from pydantic import SecretStr

from src.core.configs.auth import AuthSettings
from src.core.security import (
    create_access_token,
    create_entra_state_token,
    decode_access_token,
    decode_entra_state_token,
    hash_password,
    hash_token,
    new_opaque_token,
    pkce_challenge,
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

    # SetPasswordRequest caps at 72 *characters*; bcrypt's limit is 72 *bytes*. bcrypt < 5
    # truncated silently, bcrypt >= 5 raises — these pin the truncating behaviour every
    # existing hash was made with.
    LONG = "é" * 72  # 72 chars, 144 UTF-8 bytes

    def test_password_over_72_bytes_can_be_set_and_verified(self) -> None:
        assert verify_password(self.LONG, hash_password(self.LONG))

    def test_hash_made_by_truncating_bcrypt_still_verifies(self) -> None:
        # What bcrypt 4 stored for LONG: the hash of its first 72 bytes.
        legacy = bcrypt.hashpw(self.LONG.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")
        assert verify_password(self.LONG, legacy)

    def test_only_the_first_72_bytes_count(self) -> None:
        base = "a" * 72
        assert verify_password(base + "anything-after", hash_password(base))


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


class TestEntraStateToken:
    def test_roundtrip(self) -> None:
        token = create_entra_state_token("state-1", "nonce-1", "verifier-1", AUTH)
        claims = decode_entra_state_token(token, AUTH)
        assert claims["state"] == "state-1"
        assert claims["nonce"] == "nonce-1"
        assert claims["code_verifier"] == "verifier-1"
        assert claims["typ"] == "entra_state"

    def test_access_token_rejected_as_state(self) -> None:
        """typ confusion: a bearer access token must never pass as OAuth state."""
        token = create_access_token(uuid.uuid4(), AUTH)
        with pytest.raises(jwt.InvalidTokenError):
            decode_entra_state_token(token, AUTH)

    def test_state_token_rejected_as_access(self) -> None:
        """...and the reverse: state can never be replayed as a bearer token."""
        token = create_entra_state_token("s", "n", "v", AUTH)
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(token, AUTH)

    def test_wrong_secret_rejected(self) -> None:
        token = create_entra_state_token("s", "n", "v", AUTH)
        other = AUTH.model_copy(
            update={"jwt_secret": SecretStr("other-secret-0123456789-0123456789")}
        )
        with pytest.raises(jwt.InvalidTokenError):
            decode_entra_state_token(token, other)


class TestPkceChallenge:
    def test_rfc7636_vector(self) -> None:
        # Appendix B of RFC 7636: the canonical verifier/challenge pair.
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        assert pkce_challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

    def test_unpadded(self) -> None:
        assert "=" not in pkce_challenge(new_opaque_token())
