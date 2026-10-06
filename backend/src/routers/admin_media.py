from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.datastructures import UploadFile

from src.core.dependencies.admin_scope import require_power_admin
from src.core.dependencies.media_library import get_media_usage_service
from src.core.dependencies.storage import require_media_service
from src.core.media_paths import media_path
from src.schemas.admin_media import (
    MediaFileOut,
    MediaLibraryResponse,
    MediaUploadOut,
    MediaUseOut,
)
from src.services.exceptions import NotFoundError, PayloadTooLargeError
from src.services.media_service import MAX_UPLOAD_BYTES, MediaService
from src.services.media_usage_service import MediaUsageService

__all__ = ["router"]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["media"])

RequiredMediaDep = Annotated[MediaService, Depends(require_media_service)]
MediaUsageServiceDep = Annotated[MediaUsageService, Depends(get_media_usage_service)]


@router.post(
    "/media",
    response_model=MediaUploadOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_power_admin)],
)
async def upload_media(
    request: Request,
    media_service: Annotated[MediaService, Depends(require_media_service)],
) -> MediaUploadOut:
    """Multipart field `file`. Content-Length is checked against the largest
    per-kind limit (300 MiB, video) BEFORE the body is read at all; the
    service's own per-kind check against the actual spooled size remains
    authoritative, and the body is streamed to blob storage (never read into
    memory). A declarative `file: UploadFile = File(...)` parameter can't be
    used here: FastAPI parses the whole multipart body before any Depends()
    runs, which would defeat the fast-fail.
    """
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            oversized = int(content_length) > MAX_UPLOAD_BYTES
        except ValueError:
            oversized = False
        if oversized:
            raise PayloadTooLargeError(MAX_UPLOAD_BYTES)

    # Context-managed so the multipart parser's spooled temp files are disposed
    # deterministically. The whole upload happens INSIDE the block: the service
    # streams `upload.file` (never reads it into memory), so the spool must stay
    # alive until upload_blob has finished.
    async with request.form() as form:
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(status_code=422, detail="file is required")

        # Hand the SDK the spooled file object; the service validates type (415)
        # and size (413) before consuming it. `upload.size` is the parser's byte
        # count (a trusted fast path), not the client Content-Length header.
        result = await media_service.upload(
            content_type=upload.content_type or "",
            stream=upload.file,
            size=upload.size,
        )
        return MediaUploadOut(
            blob_path=result.blob_path,
            url=result.url,
            content_type=result.content_type,
            size_bytes=result.size_bytes,
        )


@router.get(
    "/media", response_model=MediaLibraryResponse, dependencies=[Depends(require_power_admin)]
)
async def media_library(
    media: RequiredMediaDep, usage_service: MediaUsageServiceDep
) -> MediaLibraryResponse:
    """Every uploaded file with where it is used (B6). Two services, so the
    router orchestrates: storage lists, the usage service scans lessons and
    live AI proposals."""
    files = await media.list_files()
    usage = await usage_service.usage()
    out: list[MediaFileOut] = []
    for stored in files:
        use = usage.get(stored.path)
        out.append(
            MediaFileOut(
                path=stored.path,
                kind=stored.kind,
                size_bytes=stored.size_bytes,
                uploaded_at=stored.uploaded_at,
                preview_url=media.sas_url(stored.path) if stored.kind == "image" else None,
                used_in=[
                    MediaUseOut(lesson_id=lesson_id, lesson_title=title, module_title=module)
                    for lesson_id, title, module in (use.lessons if use else [])
                ],
                proposals=use.proposals if use else 0,
            )
        )
    return MediaLibraryResponse(files=out, total_bytes=sum(f.size_bytes for f in files))


@router.delete(
    "/media/{kind}/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_power_admin)],
)
async def delete_media(
    kind: str, name: str, media: RequiredMediaDep, usage_service: MediaUsageServiceDep
) -> None:
    """Unused files only, re-checked now (409 names where it is used). Only
    upload-shaped names (`images|videos/<32 hex>.<ext>`) reach storage."""
    path = media_path(kind, name)
    if path is None:
        raise NotFoundError("Media file")
    await usage_service.ensure_unused(path)
    if not await media.delete_file(path):
        raise NotFoundError("Media file")
    logger.info("media deleted: path=%s", path)
