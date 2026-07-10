from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.datastructures import UploadFile

from src.core.dependencies.auth import require_admin
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
    dependencies=[Depends(require_admin)],
)
async def upload_media(
    request: Request,
    media_service: Annotated[MediaService, Depends(require_media_service)],
) -> MediaUploadOut:
    """Multipart field `file`. Content-Length is checked against the largest
    per-kind limit (300 MiB, video) BEFORE the body is read at all; the
    service's own per-kind check against the actual bytes remains
    authoritative. A declarative `file: UploadFile = File(...)` parameter
    can't be used here: FastAPI parses the whole multipart body before any
    Depends() runs, which would defeat the fast-fail.
    """
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            oversized = int(content_length) > MAX_UPLOAD_BYTES
        except ValueError:
            oversized = False
        if oversized:
            raise PayloadTooLargeError(MAX_UPLOAD_BYTES)

    form = await request.form()
    upload = form.get("file")
    if not isinstance(upload, UploadFile):
        raise HTTPException(status_code=422, detail="file is required")

    data = await upload.read()
    result = await media_service.upload(content_type=upload.content_type or "", data=data)
    return MediaUploadOut(
        blob_path=result.blob_path,
        url=result.url,
        content_type=result.content_type,
        size_bytes=result.size_bytes,
    )
