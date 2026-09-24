from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import bcrypt
import jwt

if TYPE_CHECKING:
    from src.core.configs.auth import AuthSettings

__all__ = [
    "create_access_token",
    "create_entra_state_token",
    "decode_access_token",
    "decode_entra_state_token",
    "hash_password",
    "hash_token",
    "new_opaque_token",
    "pkce_challenge",
    "verify_password",
]

# The OAuth handshake (authorize redirect → callback) must finish within this window.
ENTRA_STATE_TTL_MINUTES = 10


# bcrypt only ever reads the first 72 bytes. bcrypt < 5 truncated silently and every stored hash
# was made that way; bcrypt >= 5 raises instead. SetPasswordRequest caps at 72 *characters*, which
# can be up to 288 UTF-8 bytes, so truncate explicitly here — without it, users with a long
# non-ASCII password could no longer log in.
_BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID, auth: AuthSettings) -> str:
    """Self-issued HS256 JWT. Deliberately carries no role claim — role is read
    from the users table on every request (see design-backend.md §2)."""
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=auth.access_token_minutes),
        "iss": auth.jwt_issuer,
        "aud": auth.jwt_audience,
        "typ": "access",
    }
    return jwt.encode(claims, auth.jwt_secret.get_secret_value(), algorithm="HS256")


def decode_access_token(token: str, auth: AuthSettings) -> dict[str, Any]:
    """Validate signature/exp/iss/aud and return the claims.

    Raises jwt.InvalidTokenError (any subclass) on failure. This is the
    identity-provider seam: an Entra ID swap replaces only this function's body
    (PyJWKClient + RS256 + Entra audience).
    """
    claims: dict[str, Any] = jwt.decode(
        token,
        auth.jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        audience=auth.jwt_audience,
        issuer=auth.jwt_issuer,
        options={"require": ["exp", "iat", "sub"]},
    )
    if claims.get("typ") != "access":
        msg = "not an access token"
        raise jwt.InvalidTokenError(msg)
    return claims


def create_entra_state_token(state: str, nonce: str, code_verifier: str, auth: AuthSettings) -> str:
    """Sign the Entra OAuth handshake state into a short-lived JWT carried by a
    transient HttpOnly cookie between /entra/login and /entra/callback."""
    now = datetime.now(UTC)
    claims = {
        "state": state,
        "nonce": nonce,
        "code_verifier": code_verifier,
        "iat": now,
        "exp": now + timedelta(minutes=ENTRA_STATE_TTL_MINUTES),
        "iss": auth.jwt_issuer,
        "aud": auth.jwt_audience,
        "typ": "entra_state",
    }
    return jwt.encode(claims, auth.jwt_secret.get_secret_value(), algorithm="HS256")


def decode_entra_state_token(token: str, auth: AuthSettings) -> dict[str, Any]:
    """Raises jwt.InvalidTokenError on failure. Requires typ == "entra_state" so
    an access token can never stand in for handshake state (and vice versa —
    decode_access_token rejects typ != "access" symmetrically)."""
    claims: dict[str, Any] = jwt.decode(
        token,
        auth.jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        audience=auth.jwt_audience,
        issuer=auth.jwt_issuer,
        options={"require": ["exp", "iat", "state", "nonce", "code_verifier"]},
    )
    if claims.get("typ") != "entra_state":
        msg = "not an entra state token"
        raise jwt.InvalidTokenError(msg)
    return claims


def new_opaque_token() -> str:
    """43-char URL-safe random token for refresh sessions and invite/reset links."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """SHA-256 hex digest — the only form of an opaque token that is ever stored."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def pkce_challenge(code_verifier: str) -> str:
    """S256 code challenge: BASE64URL(SHA256(verifier)), unpadded (RFC 7636)."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
