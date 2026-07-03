from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.core.dependencies.auth import get_token_service
from src.core.dependencies.ratelimit import get_rate_limiter
from src.core.dependencies.user import get_user_service
from src.core.ratelimit import RateLimiter
from src.schemas.auth import (
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
from src.services.token_service import TokenPair, TokenPurpose, TokenService
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
_RATE_LIMITED = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too many attempts — try again in a minute",
    headers={"Retry-After": "60"},
)


def _pair_response(pair: TokenPair) -> TokenPairResponse:
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )


@router.post("/login", response_model=TokenPairResponse)
async def login(
    body: LoginRequest,
    user_service: UserServiceDep,
    token_service: TokenServiceDep,
    limiter: RateLimiterDep,
) -> TokenPairResponse:
    if limiter.is_limited(f"login:{body.email.strip().lower()}"):
        raise _RATE_LIMITED
    try:
        user = await user_service.authenticate(body.email, body.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return _pair_response(await token_service.issue_pair(user))


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(body: RefreshRequest, token_service: TokenServiceDep) -> TokenPairResponse:
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
        # The DB CHECK constraint restricts purpose to invite|reset.
        purpose=cast("TokenPurpose", auth_token.purpose),
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
    client_ip = request.client.host if request.client is not None else "unknown"
    if limiter.is_limited(f"set-password:{client_ip}"):
        raise _RATE_LIMITED
    try:
        _, user = await token_service.consume_action_token(body.token)
    except TokenNotFoundError as exc:
        raise _INVALID_LINK from exc
    except TokenExpiredError as exc:
        raise _EXPIRED_LINK from exc
    await user_service.set_password(user, body.password)
    await token_service.revoke_all_for_user(user.id)
    return _pair_response(await token_service.issue_pair(user))
