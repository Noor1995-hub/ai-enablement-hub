from __future__ import annotations

__all__ = [
    "AuthError",
    "InvalidCredentialsError",
    "InvalidSessionError",
    "TokenExpiredError",
    "TokenNotFoundError",
]


class AuthError(Exception):
    """Base for auth use-case failures; routers map subclasses to HTTP errors."""


class InvalidCredentialsError(AuthError):
    """Login failed (unknown email, wrong password, no password set, inactive). → 401"""


class InvalidSessionError(AuthError):
    """Refresh token unknown, revoked, expired, or its user is gone/inactive. → 401"""


class TokenNotFoundError(AuthError):
    """Invite/reset token unknown, already used, or its user is gone/inactive. → 404"""


class TokenExpiredError(AuthError):
    """Invite/reset token exists but is past its expiry. → 410"""
