from __future__ import annotations

import math
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.core.client_ip import client_ip
from src.core.configs.settings import Settings
from src.core.dependencies.auth import get_token_service
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.dependencies.settings import get_settings
from src.core.dependencies.user import get_user_service
from src.core.ratelimit import RateLimiter
from src.schemas.auth import (
    AuthMethodsResponse,
    InviteInfoResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SetPasswordRequest,
    TokenPairResponse,
)
from src.services.exceptions import (
    InvalidCredentialsError,
    InvalidSessionError,
    TokenExpiredError,
    TokenNotFoundError,
)
from src.services.token_service import ActionPurpose, TokenPair, TokenService
from src.services.user_service import UserService

__all__ = ["router"]

router = APIRouter(prefix="/api/auth", tags=["auth"])

UserServiceDep = Annotated[UserService, Depends(get_user_service)]
TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]

_INVALID_LINK = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or already-used link"
)
_EXPIRED_LINK = HTTPException(status_code=status.HTTP_410_GONE, detail="This link has expired")

# Refresh is unauthenticated (the presented token IS the credential), so the only
# key is the client IP. A whole delaware office sits behind one NAT IP, and a
# workshop that logs in together at 09:00 has every 30-minute access token expire
# together at 09:30 (doubled by multi-tab losers, whose benign 401s count too).
# A refresh token is a 256-bit opaque value, so this bounds DB load from a replay
# flood, not guessability: set high enough that a room never trips it.
_REFRESH_MAX_CALLS = 300
_REFRESH_WINDOW_SECONDS = 300.0

# Per-IP login counter, FAILED attempts only. The per-email counter (5/60s,
# every attempt) does the per-account work; this one bounds a password spray
# across many accounts from one host. It counts failures only because a whole
# office logs in from one NAT IP: a room of correct passwords must never lock
# itself out, and a successful login must not spend the room's budget.
_LOGIN_IP_MAX_FAILURES = 100
_LOGIN_IP_WINDOW_SECONDS = 300.0


def _rate_limited(limiter: RateLimiter, key: str, *, window_seconds: float) -> HTTPException:
    """429 whose Retry-After and message report the key's real remaining window
    (the Login page shows this message verbatim)."""
    seconds = limiter.retry_after(key, window_seconds=window_seconds)
    wait = "a minute" if seconds <= 60 else f"{math.ceil(seconds / 60)} minutes"
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Too many attempts — try again in {wait}",
        headers={"Retry-After": str(seconds)},
    )


def _enforce(
    limiter: RateLimiter, key: str, *, max_calls: int = 5, window_seconds: float = 60.0
) -> None:
    """Record one attempt for `key`; raise the 429 once it is past the limit."""
    if limiter.is_limited(key, max_calls=max_calls, window_seconds=window_seconds):
        raise _rate_limited(limiter, key, window_seconds=window_seconds)


def _pair_response(pair: TokenPair) -> TokenPairResponse:
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.get("/methods", response_model=AuthMethodsResponse)
async def auth_methods(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthMethodsResponse:
    """Which sign-in methods this deployment offers (the login page uses this
    to decide whether to show the Microsoft button). Public, never fails."""
    return AuthMethodsResponse(password=True, entra=settings.entra is not None)


@router.post("/login", response_model=TokenPairResponse)
async def login(
    body: LoginRequest,
    request: Request,
    user_service: UserServiceDep,
    token_service: TokenServiceDep,
    limiter: RateLimiterDep,
) -> TokenPairResponse:
    """Exchange email + password for a token pair. Rate-limited per account and,
    for failed attempts, per client."""
    # Two independent counters. login:{email} records every attempt against one
    # account (5/60s). login-ip:{ip} (client_ip: see core/client_ip.py) is meant
    # to count only FAILED password checks, but it is charged here at entry and
    # refunded on success rather than recorded after the check: authenticate()
    # yields (DB lookup, then bcrypt in a thread pool), so recording afterwards
    # would let K pipelined requests all pass while the count is under the cap
    # (~100 + K guesses per window). A spent budget refuses even a correct
    # password, before any credential work.
    ip_key = f"login-ip:{client_ip(request)}"
    ip_limited, ip_window = limiter.charge(
        ip_key, max_calls=_LOGIN_IP_MAX_FAILURES, window_seconds=_LOGIN_IP_WINDOW_SECONDS
    )
    if ip_limited:
        raise _rate_limited(limiter, ip_key, window_seconds=_LOGIN_IP_WINDOW_SECONDS)
    try:
        _enforce(limiter, f"login:{body.email.strip().lower()}")
    except HTTPException:
        # Refused before any password check: not a failure to charge the client.
        limiter.refund(ip_key, window_start=ip_window)
        raise
    try:
        user = await user_service.authenticate(body.email, body.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    # A success must not spend the office NAT IP's shared budget.
    limiter.refund(ip_key, window_start=ip_window)
    return _pair_response(await token_service.issue_pair(user))


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    token_service: TokenServiceDep,
    limiter: RateLimiterDep,
) -> TokenPairResponse:
    """Rotate the refresh token for a new pair. Rate-limited per client."""
    # Keyed on client_ip: see core/client_ip.py for which address that is and why.
    _enforce(
        limiter,
        f"refresh:{client_ip(request)}",
        max_calls=_REFRESH_MAX_CALLS,
        window_seconds=_REFRESH_WINDOW_SECONDS,
    )
    try:
        pair = await token_service.refresh_pair(body.refresh_token)
    except InvalidSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return _pair_response(pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, token_service: TokenServiceDep) -> None:
    """The refresh token itself is the credential; revocation is idempotent so
    the response never reveals whether the token existed."""
    await token_service.revoke_session(body.refresh_token)


@router.get("/invite/{token}", response_model=InviteInfoResponse)
async def invite_info(token: str, token_service: TokenServiceDep) -> InviteInfoResponse:
    """Validate an invite/reset link without consuming it (the set-password page
    calls this on load)."""
    try:
        auth_token, user = await token_service.peek_action_token(token)
    except TokenNotFoundError as exc:
        raise _INVALID_LINK from exc
    except TokenExpiredError as exc:
        raise _EXPIRED_LINK from exc
    return InviteInfoResponse(
        # peek_action_token only returns tokens whose purpose is in _ACTION_PURPOSES.
        purpose=cast("ActionPurpose", auth_token.purpose),
        email=user.email,
        first_name=user.first_name,
    )


@router.post("/set-password", response_model=TokenPairResponse)
async def set_password(
    body: SetPasswordRequest,
    request: Request,
    user_service: UserServiceDep,
    token_service: TokenServiceDep,
    limiter: RateLimiterDep,
) -> TokenPairResponse:
    """Complete an invite or reset: consume the token, set the password, revoke
    all other outstanding tokens/sessions, and auto-login."""
    _enforce(limiter, f"set-password:{client_ip(request)}")
    try:
        _, user = await token_service.consume_action_token(body.token)
    except TokenNotFoundError as exc:
        raise _INVALID_LINK from exc
    except TokenExpiredError as exc:
        raise _EXPIRED_LINK from exc
    await user_service.set_password(user, body.password)
    await token_service.revoke_all_for_user(user.id)
    return _pair_response(await token_service.issue_pair(user))
