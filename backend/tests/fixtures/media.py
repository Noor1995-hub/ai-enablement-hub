"""Media test doubles: StorageSettings for tests plus a recording stand-in
for BlobServiceClient.get_blob_client (SAS generation is offline HMAC, so no
network double is needed for that half of MediaService)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import SecretStr

from src.core.configs.storage import StorageSettings

__all__ = ["TEST_STORAGE", "RecordingUploader", "UploadCall"]

# Any base64 string works as an account key: from_connection_string and SAS
# generation are both pure/offline, no real Azure credential is needed.
TEST_STORAGE = StorageSettings(
    connection_string=SecretStr(
        "AccountName=testacct;"
        "AccountKey=dW5pdC10ZXN0LXN0b3JhZ2UtYWNjb3VudC1rZXktMzI=;"
        "EndpointSuffix=core.windows.net"
    ),
)


@dataclass
class UploadCall:
    container: str
    blob: str
    data: bytes
    length: int | None
    overwrite: bool | None
    content_type: str | None


class _FakeBlobClient:
    def __init__(self, calls: list[UploadCall], container: str, blob: str) -> None:
        self._calls = calls
        self._container = container
        self._blob = blob

    def upload_blob(
        self,
        data: Any,
        *,
        length: int | None = None,
        overwrite: bool | None = None,
        content_settings: Any = None,
        **kwargs: Any,
    ) -> None:
        # Production hands upload_blob the spooled multipart file object (a
        # stream), not bytes; read it here so tests can still assert on the
        # real uploaded content and prove the stream was rewound.
        content = bytes(data) if isinstance(data, bytes | bytearray) else data.read()
        self._calls.append(
            UploadCall(
                container=self._container,
                blob=self._blob,
                data=content,
                length=length,
                overwrite=overwrite,
                content_type=getattr(content_settings, "content_type", None),
            )
        )


class RecordingUploader:
    """Stands in for BlobServiceClient: get_blob_client returns a fake
    BlobClient whose upload_blob records the call instead of doing network
    I/O. Every upload succeeds."""

    def __init__(self) -> None:
        self.calls: list[UploadCall] = []

    def get_blob_client(self, container: str, blob: str) -> _FakeBlobClient:
        return _FakeBlobClient(self.calls, container, blob)
