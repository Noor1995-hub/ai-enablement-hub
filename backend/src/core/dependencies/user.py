from __future__ import annotations

from typing import Annotated

from fastapi import Depends

# Runtime imports on purpose: FastAPI must resolve these names when it
# evaluates the deferred parameter annotations below (see database.py).
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies.database import get_session
from src.repositories.user_repository import UserRepository
from src.services.user_service import UserService

__all__ = ["get_user_repository", "get_user_service"]


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRepository:
    return UserRepository(session)


def get_user_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(repository)
