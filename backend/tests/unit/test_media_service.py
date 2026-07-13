"""MediaService: content-type/size validation, uuid-hex blob naming (never
the client filename), threadpool-wrapped upload, and sas_url's offline HMAC
SAS math (start quantized to midnight UTC, read-only, HTTPS-only). Pure unit
tests with a recording stub uploader (AAA, no network)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import pytest

from src.services.exceptions import PayloadTooLargeError, UnsupportedMediaTypeError
from src.services.media_service import MediaService
from tests.fixtures.media import TEST_STORAGE, RecordingUploader

_UUID_HEX = "[0-9a-f]{32}"


def _service(
    uploader: RecordingUploader | None = None, *, sas_ttl_hours: int = 48
) -> tuple[MediaService, RecordingUploader]:
    uploader = uploader or RecordingUploader()
    service = MediaService(
        uploader,
        account_name=TEST_STORAGE.account_name,
        account_key=TEST_STORAGE.account_key.get_secret_value(),
        blob_endpoint=TEST_STORAGE.blob_endpoint,
        container=TEST_STORAGE.container,
        sas_ttl_hours=sas_ttl_hours,
    )
    return service, uploader


class TestSasUrl:
    def test_url_contains_container_and_blob_path(self) -> None:
        service, _ = _service()
        url = service.sas_url("images/abc123.png")
        assert url.startswith(f"{TEST_STORAGE.blob_endpoint}/{TEST_STORAGE.container}/")
        assert "images/abc123.png" in url

    def test_query_carries_sig_se_st(self) -> None:
        service, _ = _service()
        query = parse_qs(urlparse(service.sas_url("images/abc.png")).query)
        assert "sig" in query
        assert "se" in query
        assert "st" in query

    def test_st_is_midnight_utc(self) -> None:
        service, _ = _service()
        query = parse_qs(urlparse(service.sas_url("images/abc.png")).query)
        start = datetime.strptime(query["st"][0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        assert (start.hour, start.minute, start.second, start.microsecond) == (0, 0, 0, 0)

    def test_expiry_minus_start_equals_ttl_hours(self) -> None:
        service, _ = _service(sas_ttl_hours=72)
        query = parse_qs(urlparse(service.sas_url("images/abc.png")).query)
        start = datetime.strptime(query["st"][0], "%Y-%m-%dT%H:%M:%SZ")
        expiry = datetime.strptime(query["se"][0], "%Y-%m-%dT%H:%M:%SZ")
        assert (expiry - start).total_seconds() == 72 * 3600

    def test_default_ttl_is_48_hours(self) -> None:
        service, _ = _service()
        query = parse_qs(urlparse(service.sas_url("images/abc.png")).query)
        start = datetime.strptime(query["st"][0], "%Y-%m-%dT%H:%M:%SZ")
        expiry = datetime.strptime(query["se"][0], "%Y-%m-%dT%H:%M:%SZ")
        assert (expiry - start).total_seconds() == 48 * 3600

    def test_permission_is_read_only(self) -> None:
        service, _ = _service()
        query = parse_qs(urlparse(service.sas_url("images/abc.png")).query)
        assert query["sp"] == ["r"]

    def test_https_only(self) -> None:
        service, _ = _service()
        query = parse_qs(urlparse(service.sas_url("images/abc.png")).query)
        assert query["spr"] == ["https"]


class TestUploadValidation:
    async def test_png_upload_returns_images_prefixed_blob_path(self) -> None:
        service, _ = _service()
        content = b"\x89PNG fake bytes"
        result = await service.upload(content_type="image/png", stream=BytesIO(content))
        assert re.fullmatch(rf"images/{_UUID_HEX}\.png", result.blob_path)
        assert result.content_type == "image/png"
        assert result.size_bytes == len(content)
        assert result.url == service.sas_url(result.blob_path)

    @pytest.mark.parametrize(
        ("content_type", "ext"),
        [
            ("image/png", ".png"),
            ("image/jpeg", ".jpg"),
            ("image/webp", ".webp"),
            ("image/gif", ".gif"),
            ("video/mp4", ".mp4"),
            ("video/webm", ".webm"),
        ],
    )
    async def test_extension_is_mapped_from_content_type(self, content_type: str, ext: str) -> None:
        service, _ = _service()
        result = await service.upload(content_type=content_type, stream=BytesIO(b"data"))
        assert result.blob_path.endswith(ext)

    async def test_video_upload_returns_videos_prefixed_blob_path(self) -> None:
        service, _ = _service()
        result = await service.upload(content_type="video/mp4", stream=BytesIO(b"fake mp4 bytes"))
        assert re.fullmatch(rf"videos/{_UUID_HEX}\.mp4", result.blob_path)

    async def test_blob_name_is_never_derived_from_a_filename(self) -> None:
        """upload() takes no filename parameter at all — the name is always
        kind/uuid4().hex + mapped extension."""
        service, _ = _service()
        result = await service.upload(content_type="image/png", stream=BytesIO(b"data"))
        assert "malicious" not in result.blob_path
        # The path segment (sans extension) must be exactly a uuid4 hex digest.
        name = result.blob_path.removeprefix("images/").removesuffix(".png")
        assert uuid.UUID(hex=name).hex == name

    async def test_upload_is_called_with_overwrite_false_and_content_settings(self) -> None:
        service, uploader = _service()
        await service.upload(content_type="image/png", stream=BytesIO(b"data"))
        [call] = uploader.calls
        assert call.overwrite is False
        assert call.content_type == "image/png"
        assert call.data == b"data"

    async def test_upload_streams_full_content_with_length(self) -> None:
        """The spooled stream (not a bytes copy) is handed to the SDK with an
        explicit length; the recorded content proves it was rewound and fully
        readable from position 0."""
        service, uploader = _service()
        content = b"\x00\x01\x02 body of the upload"
        await service.upload(content_type="image/png", stream=BytesIO(content))
        [call] = uploader.calls
        assert call.data == content
        assert call.length == len(content)

    async def test_upload_rewinds_a_stream_left_at_eof(self) -> None:
        """size=None forces the service to measure the stream by seeking to the
        end; it must rewind before uploading so no bytes are lost."""
        service, uploader = _service()
        content = b"already-read stream contents"
        stream = BytesIO(content)
        stream.read()  # leave the cursor at EOF
        result = await service.upload(content_type="video/mp4", stream=stream, size=None)
        [call] = uploader.calls
        assert call.data == content
        assert result.size_bytes == len(content)

    @pytest.mark.parametrize("content_type", ["text/plain", "image/svg+xml", "application/pdf", ""])
    async def test_unsupported_content_type_is_rejected(self, content_type: str) -> None:
        service, uploader = _service()
        with pytest.raises(UnsupportedMediaTypeError):
            await service.upload(content_type=content_type, stream=BytesIO(b"data"))
        assert uploader.calls == []

    async def test_oversize_image_is_rejected(self) -> None:
        service, uploader = _service()
        oversize = b"x" * (10 * 1024 * 1024 + 1)
        with pytest.raises(PayloadTooLargeError):
            await service.upload(content_type="image/png", stream=BytesIO(oversize))
        assert uploader.calls == []

    async def test_oversize_is_rejected_by_measured_stream_when_size_absent(self) -> None:
        """With no size hint the check falls back to measuring the actual
        spooled stream — that measurement stays authoritative."""
        service, uploader = _service()
        oversize = b"x" * (10 * 1024 * 1024 + 1)
        with pytest.raises(PayloadTooLargeError):
            await service.upload(content_type="image/png", stream=BytesIO(oversize), size=None)
        assert uploader.calls == []

    async def test_image_at_exact_max_size_is_accepted(self) -> None:
        service, _ = _service()
        exactly_max = b"x" * (10 * 1024 * 1024)
        result = await service.upload(content_type="image/png", stream=BytesIO(exactly_max))
        assert result.size_bytes == 10 * 1024 * 1024

    async def test_oversize_video_is_rejected(self) -> None:
        service, uploader = _service()
        # One byte over the 300 MiB video cap.
        oversize = b"x" * (300 * 1024 * 1024 + 1)
        with pytest.raises(PayloadTooLargeError):
            await service.upload(content_type="video/mp4", stream=BytesIO(oversize))
        assert uploader.calls == []

    async def test_image_sized_video_is_not_rejected_by_the_image_cap(self) -> None:
        """A video just over the 10 MiB image cap must still be accepted —
        proves the size limit is chosen by the upload's own kind."""
        service, _ = _service()
        data = b"x" * (11 * 1024 * 1024)
        result = await service.upload(content_type="video/mp4", stream=BytesIO(data))
        assert result.size_bytes == 11 * 1024 * 1024


class TestStampBlocks:
    async def test_stamp_blocks_delegates_to_sas_url(self) -> None:
        service, _ = _service()
        blocks = [{"id": "b1", "type": "image", "blob_path": "images/abc.png"}]
        [result] = service.stamp_blocks(blocks)
        assert result["url"] == service.sas_url("images/abc.png")

    async def test_stamp_blocks_leaves_embed_video_untouched(self) -> None:
        service, _ = _service()
        blocks = [{"id": "b2", "type": "video", "source": "embed", "url": "https://youtu.be/x"}]
        [result] = service.stamp_blocks(blocks)
        assert result["url"] == "https://youtu.be/x"
