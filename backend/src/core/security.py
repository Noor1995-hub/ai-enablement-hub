from __future__ import annotations

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
    "decode_access_token",
    "hash_password",
    "hash_token",
    "new_opaque_token",
    "verify_password",
]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
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


def new_opaque_token() -> str:
    """43-char URL-safe random token for refresh sessions and invite/reset links."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """SHA-256 hex digest — the only form of an opaque token that is ever stored."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
