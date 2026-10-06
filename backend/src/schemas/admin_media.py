from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

__all__ = [
    "MediaFileOut",
    "MediaLibraryResponse",
    "MediaUploadOut",
    "MediaUseOut",
]


class MediaUploadOut(BaseModel):
    """`url` is a freshly-stamped SAS for instant admin-side preview; it is
    never persisted (the lesson stores `blob_path` only)."""

    blob_path: str
    url: str
    content_type: str
    size_bytes: int


class MediaUseOut(BaseModel):
    lesson_id: uuid.UUID
    lesson_title: str
    module_title: str


class MediaFileOut(BaseModel):
    """One file in the media library (B6). `preview_url` is a short-lived SAS for
    images, null for videos; `used_in` empty and `proposals` 0 means unused."""

    path: str
    kind: Literal["image", "video"]
    size_bytes: int
    uploaded_at: datetime
    preview_url: str | None
    used_in: list[MediaUseOut]
    proposals: int


class MediaLibraryResponse(BaseModel):
    files: list[MediaFileOut]
    total_bytes: int
