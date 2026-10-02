from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Runtime imports on purpose: FastAPI must resolve these names when it
# evaluates the deferred parameter annotations below (see database.py).
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.configs.settings import Settings
from src.core.dependencies.database import get_session
from src.core.dependencies.settings import get_settings
from src.core.dependencies.user import get_user_repository, get_user_service
from src.core.security import decode_access_token
from src.db.models import User
from src.repositories.auth_session_repository import AuthSessionRepository
from src.repositories.auth_token_repository import AuthTokenRepository
from src.repositories.user_repository import UserRepository
from src.services.token_service import TokenService
from src.services.user_service import UserService

__all__ = [
    "get_auth_session_repository",
    "get_auth_token_repository",
    "get_current_user",
    "get_token_service",
]

_bearer = HTTPBearer(auto_error=False)


def get_auth_token_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthTokenRepository:
    return AuthTokenRepository(session)


def get_auth_session_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthSessionRepository:
    return AuthSessionRepository(session)


def get_token_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    tokens: Annotated[AuthTokenRepository, Depends(get_auth_token_repository)],
    sessions: Annotated[AuthSessionRepository, Depends(get_auth_session_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenService:
    return TokenService(users, tokens, sessions, settings.auth)


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """The single authz entry point: validate the bearer JWT and load the user
    row. Role deliberately comes from the DB, not the token (design-backend §2/§4)."""
    if credentials is None:
        raise _unauthorized("Not authenticated")
    try:
        claims = decode_access_token(credentials.credentials, settings.auth)
        user_id = uuid.UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise _unauthorized("Invalid or expired token") from exc
    user = await user_service.get_active_user(user_id)
    if user is None:
        raise _unauthorized("Invalid or expired token")
    return user
