from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.datastructures import UploadFile

from src.core.dependencies.admin_scope import require_power_admin
from src.core.dependencies.storage import require_media_service
from src.schemas.admin_media import MediaUploadOut
from src.services.exceptions import PayloadTooLargeError
from src.services.media_service import MAX_UPLOAD_BYTES, MediaService

__all__ = ["router"]

router = APIRouter(prefix="/api/admin", tags=["media"])


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
