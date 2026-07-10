from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple, Protocol

from azure.storage.blob import BlobSasPermissions, ContentSettings, generate_blob_sas
from starlette.concurrency import run_in_threadpool

from src.services.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError
from src.services.media_blocks import stamp_urls

__all__ = ["MAX_UPLOAD_BYTES", "BlobUploader", "MediaService", "UploadedMedia"]

# Content type -> file extension; the extension is NEVER taken from the
# client's filename (spoofed-extension / path-traversal risk). No SVG: it can
# carry embedded <script>.
_IMAGE_EXTENSIONS: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_VIDEO_EXTENSIONS: dict[str, str] = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_MAX_VIDEO_BYTES = 300 * 1024 * 1024
# The largest per-kind limit. The router's fast-fail Content-Length precheck
# uses this: it can't know the media kind before the body is parsed.
MAX_UPLOAD_BYTES = max(_MAX_IMAGE_BYTES, _MAX_VIDEO_BYTES)


class UploadedMedia(NamedTuple):
    blob_path: str
    url: str
    content_type: str
    size_bytes: int


class BlobUploader(Protocol):
    """The one BlobServiceClient method the service needs; tests stub it with
    a recording fake."""

    def get_blob_client(self, container: str, blob: str) -> Any: ...


def _classify(content_type: str) -> tuple[str, str, int]:
    """kind, extension, max size for a content type; raises
    UnsupportedMediaTypeError for anything not on the allow-list."""
    if content_type in _IMAGE_EXTENSIONS:
        return "image", _IMAGE_EXTENSIONS[content_type], _MAX_IMAGE_BYTES
    if content_type in _VIDEO_EXTENSIONS:
        return "video", _VIDEO_EXTENSIONS[content_type], _MAX_VIDEO_BYTES
    raise UnsupportedMediaTypeError(content_type)


class MediaService:
    """Validated image/video upload to a private Blob Storage container, plus
    read-only SAS URL generation for lesson content_blocks (the stamping/
    stripping call sites at the lesson read/write boundary are a later task)."""

    def __init__(
        self,
        uploader: BlobUploader,
        *,
        account_name: str,
        account_key: str,
        blob_endpoint: str,
        container: str,
        sas_ttl_hours: int,
    ) -> None:
        self._uploader = uploader
        self._account_name = account_name
        self._account_key = account_key
        self._blob_endpoint = blob_endpoint
        self._container = container
        self._sas_ttl_hours = sas_ttl_hours

    async def upload(self, *, content_type: str, data: bytes) -> UploadedMedia:
        kind, ext, max_bytes = _classify(content_type)
        # Authoritative size check: the actual (spooled) bytes, never the
        # client-supplied Content-Length header.
        if len(data) > max_bytes:
            raise PayloadTooLargeError(max_bytes)

        blob_path = f"{kind}s/{uuid.uuid4().hex}{ext}"
        blob_client = self._uploader.get_blob_client(self._container, blob_path)
        # The SDK's BlobClient is sync — never run it on the event loop.
        await run_in_threadpool(
            blob_client.upload_blob,
            data,
            overwrite=False,
            content_settings=ContentSettings(content_type=content_type),
        )
        return UploadedMedia(
            blob_path=blob_path,
            url=self.sas_url(blob_path),
            content_type=content_type,
            size_bytes=len(data),
        )

    def sas_url(self, blob_path: str) -> str:
        """Read-only, HTTPS-only SAS. The validity window is quantized to a
        midnight-UTC start so the URL stays stable/cacheable across repeated
        reads within the same window (see StorageSettings.sas_ttl_hours)."""
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        expiry = start + timedelta(hours=self._sas_ttl_hours)
        token = generate_blob_sas(
            account_name=self._account_name,
            container_name=self._container,
            blob_name=blob_path,
            account_key=self._account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
            start=start,
            protocol="https",
        )
        return f"{self._blob_endpoint}/{self._container}/{blob_path}?{token}"

    def stamp_blocks(self, blocks: list[Any]) -> list[Any]:
        """Thin composition over the pure helper: stamps a fresh SAS `url`
        into every image/blob-video block (see media_blocks.stamp_urls)."""
        return stamp_urls(blocks, self.sas_url)
