from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from jwt import PyJWKClient

# Runtime imports on purpose: FastAPI must resolve these names when it
# evaluates the deferred parameter annotations below (see database.py).
from src.core.configs.settings import Settings
from src.core.dependencies.settings import get_settings
from src.core.dependencies.user import get_user_repository
from src.repositories.user_repository import UserRepository
from src.services.entra_service import EntraService

__all__ = ["get_entra_service"]


@lru_cache
def _jwks_client(jwks_url: str) -> PyJWKClient:
    """Process-lifetime instance so its built-in JWK-set cache is effective;
    key rotation is handled via kid lookup on cache miss."""
    return PyJWKClient(jwks_url, cache_keys=True)


def get_entra_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EntraService:
    """The Entra feature flag: without ENTRA__* config the endpoints don't exist."""
    if settings.entra is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    return EntraService(settings.entra, users, _jwks_client(settings.entra.jwks_url))
