from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import SEEK_END, SEEK_SET
from typing import Any, BinaryIO, Literal, NamedTuple, Protocol

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobSasPermissions, ContentSettings, generate_blob_sas
from starlette.concurrency import run_in_threadpool

from src.services.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError
from src.services.media_blocks import stamp_urls

__all__ = [
    "BlobUploader",
    "MAX_UPLOAD_BYTES",
    "MediaService",
    "StoredFile",
    "UploadedMedia",
]

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

    def get_container_client(self, container: str) -> Any: ...


def _classify(content_type: str) -> tuple[str, str, int]:
    """kind, extension, max size for a content type; raises
    UnsupportedMediaTypeError for anything not on the allow-list."""
    if content_type in _IMAGE_EXTENSIONS:
        return "image", _IMAGE_EXTENSIONS[content_type], _MAX_IMAGE_BYTES
    if content_type in _VIDEO_EXTENSIONS:
        return "video", _VIDEO_EXTENSIONS[content_type], _MAX_VIDEO_BYTES
    raise UnsupportedMediaTypeError(content_type)


def _stream_length(stream: BinaryIO) -> int:
    """Actual byte length of a seekable stream, measured by seeking to the end
    — never by reading it into memory (reading would negate the whole point of
    streaming the >1 MiB spooled upload off disk). Restores the cursor after."""
    current = stream.tell()
    try:
        stream.seek(0, SEEK_END)
        return stream.tell()
    finally:
        stream.seek(current, SEEK_SET)


@dataclass(frozen=True)
class StoredFile:
    """One file in the media container (B6 media library)."""

    path: str
    kind: Literal["image", "video"]
    size_bytes: int
    uploaded_at: datetime


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

    async def upload(
        self, *, content_type: str, stream: BinaryIO, size: int | None = None
    ) -> UploadedMedia:
        # Content type first, so an unsupported upload is rejected (415) before
        # the body is measured or streamed anywhere.
        kind, ext, max_bytes = _classify(content_type)
        # Authoritative size check on the ACTUAL upload bytes, never a
        # client-supplied Content-Length. `size` is the multipart parser's own
        # byte count (Starlette's UploadFile.size), a trusted fast path; when it
        # is absent we measure the spooled stream by seeking — which, unlike
        # reading, keeps the >1 MiB-to-disk spool from being pulled into RAM.
        actual_size = size if size is not None else _stream_length(stream)
        if actual_size > max_bytes:
            raise PayloadTooLargeError(max_bytes)

        blob_path = f"{kind}s/{uuid.uuid4().hex}{ext}"
        blob_client = self._uploader.get_blob_client(self._container, blob_path)
        # Upload the spooled file object itself (not its bytes) so a large video
        # stays on disk. Rewind first: the size check (or the parser) may have
        # left the cursor at EOF. The SDK's BlobClient is sync — never on the
        # event loop.
        stream.seek(0)
        await run_in_threadpool(
            blob_client.upload_blob,
            stream,
            length=actual_size,
            overwrite=False,
            content_settings=ContentSettings(content_type=content_type),
        )
        return UploadedMedia(
            blob_path=blob_path,
            url=self.sas_url(blob_path),
            content_type=content_type,
            size_bytes=actual_size,
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

    async def list_files(self) -> list[StoredFile]:
        """Every uploaded file, newest first (B6 media library). The SDK is sync:
        listing runs in the threadpool, never on the event loop."""
        container = self._uploader.get_container_client(self._container)
        blobs = await run_in_threadpool(lambda: list(container.list_blobs()))
        files = [
            StoredFile(
                path=blob.name,
                kind="image" if blob.name.startswith("images/") else "video",
                size_bytes=int(blob.size or 0),
                uploaded_at=blob.last_modified,
            )
            for blob in blobs
            if blob.name.startswith(("images/", "videos/"))
        ]
        return sorted(files, key=lambda f: f.uploaded_at, reverse=True)

    async def delete_file(self, path: str) -> bool:
        """Delete one blob; False when it does not exist."""
        blob = self._uploader.get_blob_client(self._container, path)
        try:
            await run_in_threadpool(blob.delete_blob)
        except ResourceNotFoundError:
            return False
        return True
