from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from azure.storage.blob import BlobServiceClient
from fastapi import Depends, HTTPException, status

# Runtime imports on purpose: FastAPI must resolve these names when it
# evaluates the deferred parameter annotations below (see database.py).
from src.core.configs.settings import Settings
from src.core.dependencies.settings import get_settings
from src.services.media_service import MediaService

__all__ = ["get_media_service", "require_media_service"]


@lru_cache
def _blob_service_client(connection_string: str) -> BlobServiceClient:
    """Process-lifetime client (mirrors _email_client in dependencies/email.py)."""
    return BlobServiceClient.from_connection_string(connection_string)


def get_media_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> MediaService | None:
    """None (not 404) when STORAGE__* is unconfigured: mirrors the email
    provider idiom. require_media_service below turns None into 404 for the
    endpoints that only exist when the feature is on."""
    if settings.storage is None:
        return None
    storage = settings.storage
    return MediaService(
        _blob_service_client(storage.connection_string.get_secret_value()),
        account_name=storage.account_name,
        account_key=storage.account_key.get_secret_value(),
        blob_endpoint=storage.blob_endpoint,
        container=storage.container,
        sas_ttl_hours=storage.sas_ttl_hours,
    )


def require_media_service(
    service: Annotated[MediaService | None, Depends(get_media_service)],
) -> MediaService:
    """The lesson-media feature flag: without STORAGE__* config the admin
    upload endpoint doesn't exist — same 404 idiom as get_entra_service in
    core/dependencies/entra.py."""
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    return service
