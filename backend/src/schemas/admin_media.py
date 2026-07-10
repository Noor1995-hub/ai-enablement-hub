from __future__ import annotations

from pydantic import BaseModel

__all__ = ["MediaUploadOut"]


class MediaUploadOut(BaseModel):
    """`url` is a freshly-stamped SAS for instant admin-side preview; it is
    never persisted (the lesson stores `blob_path` only)."""

    blob_path: str
    url: str
    content_type: str
    size_bytes: int
