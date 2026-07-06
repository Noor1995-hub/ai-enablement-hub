from __future__ import annotations

import secrets
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from src.core.configs.settings import Settings
from src.core.dependencies.auth import get_token_service
from src.core.dependencies.entra import get_entra_service
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.dependencies.settings import get_settings
from src.core.ratelimit import RateLimiter
from src.core.security import (
    ENTRA_STATE_TTL_MINUTES,
    create_entra_state_token,
    decode_entra_state_token,
    new_opaque_token,
    pkce_challenge,
)
from src.schemas.auth import EntraRedeemRequest, TokenPairResponse
from src.services.entra_service import EntraService
from src.services.exceptions import (
    EntraExchangeError,
    EntraUserNotFoundError,
    TokenExpiredError,
    TokenNotFoundError,
)
from src.services.token_service import TokenService

__all__ = ["router"]

router = APIRouter(prefix="/api/auth/entra", tags=["auth"])

EntraServiceDep = Annotated[EntraService, Depends(get_entra_service)]
TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

# Carries {state, nonce, code_verifier} (signed JWT) across the OAuth redirect.
# Path-scoped so the SPA never sees it; SameSite=Lax admits the top-level GET
# navigation back from login.microsoftonline.com.
_STATE_COOKIE = "entra_oidc"
_COOKIE_PATH = "/api/auth/entra"

_INVALID_CODE = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or already-used code"
)
_EXPIRED_CODE = HTTPException(status_code=status.HTTP_410_GONE, detail="This code has expired")
_RATE_LIMITED = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too many attempts — try again in a minute",
    headers={"Retry-After": "60"},
)


def _redirect_uri(settings: Settings) -> str:
    # Always from configuration, never from request headers.
    return f"{settings.app.url.rstrip('/')}/api/auth/entra/callback"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _login_error(settings: Settings, code: str) -> RedirectResponse:
    """Callback failures land on the login page as a friendly message — a
    top-level navigation must never end in a JSON error body."""
    response = RedirectResponse(
        f"{settings.app.url.rstrip('/')}/login?error={code}",
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie(_STATE_COOKIE, path=_COOKIE_PATH)
    return response


@router.get("/login")
async def entra_login(entra_service: EntraServiceDep, settings: SettingsDep) -> RedirectResponse:
    """Start the OAuth handshake: 302 to Microsoft with a fresh state/nonce/PKCE
    triple, mirrored into the signed state cookie."""
    state = new_opaque_token()
    nonce = new_opaque_token()
    code_verifier = new_opaque_token()
    response = RedirectResponse(
        entra_service.build_authorize_url(
            state=state,
            nonce=nonce,
            code_challenge=pkce_challenge(code_verifier),
            redirect_uri=_redirect_uri(settings),
        ),
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(
        _STATE_COOKIE,
        create_entra_state_token(state, nonce, code_verifier, settings.auth),
        max_age=ENTRA_STATE_TTL_MINUTES * 60,
        path=_COOKIE_PATH,
        secure=settings.app.env == "prod",
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/callback")
async def entra_callback(
    request: Request,
    entra_service: EntraServiceDep,
    token_service: TokenServiceDep,
    limiter: RateLimiterDep,
    settings: SettingsDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    entra_oidc: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    """Finish the handshake: validate state, exchange the code, resolve the
    invited user, and hand the SPA a one-time redeem code in the URL fragment
    (fragments never reach server logs)."""
    # Higher ceiling than the JSON endpoints: the callback triggers an outbound
    # exchange, but legitimate retries after Microsoft round-trips are normal.
    if limiter.is_limited(f"entra-callback:{_client_ip(request)}", max_calls=10):
        return _login_error(settings, "rate_limited")
    if error is not None:
        # The user cancelled or Microsoft refused consent — not a fault.
        return _login_error(settings, "entra_denied")
    if entra_oidc is None or code is None or state is None:
        return _login_error(settings, "invalid_state")
    try:
        handshake = decode_entra_state_token(entra_oidc, settings.auth)
    except jwt.InvalidTokenError:
        return _login_error(settings, "invalid_state")
    if not secrets.compare_digest(handshake["state"], state):
        return _login_error(settings, "invalid_state")
    try:
        id_token = await entra_service.exchange_code(
            code=code,
            code_verifier=handshake["code_verifier"],
            redirect_uri=_redirect_uri(settings),
        )
        claims = await entra_service.validate_id_token(id_token, nonce=handshake["nonce"])
    except EntraExchangeError:
        return _login_error(settings, "entra_failed")
    try:
        user = await entra_service.resolve_user(claims)
    except EntraUserNotFoundError:
        return _login_error(settings, "not_invited")
    login_code = await token_service.issue_login_code(user)
    response = RedirectResponse(
        f"{settings.app.url.rstrip('/')}/auth/callback#code={login_code}",
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie(_STATE_COOKIE, path=_COOKIE_PATH)
    return response


@router.post("/redeem", response_model=TokenPairResponse)
async def entra_redeem(
    body: EntraRedeemRequest,
    request: Request,
    _entra_service: EntraServiceDep,  # feature-flag gate only: 404 when unconfigured
    token_service: TokenServiceDep,
    limiter: RateLimiterDep,
) -> TokenPairResponse:
    """Swap the one-time login code for the app's native token pair (same
    response shape as password login)."""
    if limiter.is_limited(f"entra-redeem:{_client_ip(request)}"):
        raise _RATE_LIMITED
    try:
        _, user = await token_service.consume_login_code(body.code)
    except TokenNotFoundError as exc:
        raise _INVALID_CODE from exc
    except TokenExpiredError as exc:
        raise _EXPIRED_CODE from exc
    pair = await token_service.issue_pair(user)
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )
