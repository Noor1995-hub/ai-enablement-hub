"""POST /api/admin/media: content-type/size validation end to end through the
real router (multipart, Content-Length fast-fail, blob naming), and the
storage-unset 404 with the default (storage=None) test settings."""

from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.dependencies.database import get_session
from src.core.dependencies.settings import get_settings
from src.core.dependencies.storage import get_media_service
from src.main import app
from src.services.media_service import MAX_UPLOAD_BYTES, MediaService
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_user
from tests.fixtures.media import TEST_STORAGE, RecordingUploader

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings

_UUID_HEX = "[0-9a-f]{32}"


@pytest_asyncio.fixture
async def media_client(
    db_session: AsyncSession, test_settings: Settings
) -> AsyncGenerator[tuple[AsyncClient, RecordingUploader]]:
    """conftest's client plus a real MediaService (validation, naming, and SAS
    math all real) wired to a recording stub uploader — the router runs end
    to end, fully offline (mirrors test_admin_email.py's make_client)."""
    uploader = RecordingUploader()
    service = MediaService(
        uploader,
        account_name=TEST_STORAGE.account_name,
        account_key=TEST_STORAGE.account_key.get_secret_value(),
        blob_endpoint=TEST_STORAGE.blob_endpoint,
        container=TEST_STORAGE.container,
        sas_ttl_hours=TEST_STORAGE.sas_ttl_hours,
    )

    async def _override_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_media_service] = lambda: service
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    try:
        yield client, uploader
    finally:
        await client.aclose()
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_headers(db_session: AsyncSession, test_settings: Settings) -> dict[str, str]:
    admin = await create_user(db_session, email="media-admin@example.com", role="admin")
    return auth_headers(admin, test_settings)


class TestUploadHappyPath:
    async def test_png_upload_returns_201_with_images_blob_path(
        self,
        media_client: tuple[AsyncClient, RecordingUploader],
        admin_headers: dict[str, str],
    ) -> None:
        client, uploader = media_client
        content = b"\x89PNG\r\n fake but plausible png bytes"
        response = await client.post(
            "/api/admin/media",
            files={"file": ("photo.png", content, "image/png")},
            headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert re.fullmatch(rf"images/{_UUID_HEX}\.png", data["blob_path"])
        assert data["content_type"] == "image/png"
        assert data["size_bytes"] == len(content)
        assert data["url"]
        assert TEST_STORAGE.container in data["url"]
        [call] = uploader.calls
        assert call.blob == data["blob_path"]
        assert call.data == content
        assert call.overwrite is False

    async def test_mp4_upload_returns_201_with_videos_blob_path(
        self,
        media_client: tuple[AsyncClient, RecordingUploader],
        admin_headers: dict[str, str],
    ) -> None:
        client, uploader = media_client
        content = b"fake but plausible mp4 bytes"
        response = await client.post(
            "/api/admin/media",
            files={"file": ("clip.mp4", content, "video/mp4")},
            headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert re.fullmatch(rf"videos/{_UUID_HEX}\.mp4", data["blob_path"])
        assert data["content_type"] == "video/mp4"
        [call] = uploader.calls
        assert call.blob == data["blob_path"]

    async def test_blob_name_ignores_the_client_filename(
        self,
        media_client: tuple[AsyncClient, RecordingUploader],
        admin_headers: dict[str, str],
    ) -> None:
        client, _ = media_client
        response = await client.post(
            "/api/admin/media",
            files={"file": ("../../etc/passwd.png", b"data", "image/png")},
            headers=admin_headers,
        )
        assert response.status_code == 201
        blob_path = response.json()["blob_path"]
        assert "passwd" not in blob_path
        assert "etc" not in blob_path
        name = blob_path.removeprefix("images/").removesuffix(".png")
        # A bare uuid4 hex digest — nothing filename-derived survives.
        assert uuid.UUID(hex=name).hex == name


class TestUploadValidation:
    @pytest.mark.parametrize(
        ("filename", "content_type"),
        [("notes.txt", "text/plain"), ("image.svg", "image/svg+xml")],
    )
    async def test_disallowed_content_type_is_415(
        self,
        media_client: tuple[AsyncClient, RecordingUploader],
        admin_headers: dict[str, str],
        filename: str,
        content_type: str,
    ) -> None:
        client, uploader = media_client
        response = await client.post(
            "/api/admin/media",
            files={"file": (filename, b"<script>alert(1)</script>", content_type)},
            headers=admin_headers,
        )
        assert response.status_code == 415
        assert response.json()["error"]["code"] == "unsupported_media_type"
        assert uploader.calls == []

    async def test_oversize_image_is_413(
        self,
        media_client: tuple[AsyncClient, RecordingUploader],
        admin_headers: dict[str, str],
    ) -> None:
        """Under the router's 300 MiB fast-fail threshold but over the
        service's own 10 MiB image cap: exercises the authoritative
        spooled-size check, not the header precheck."""
        client, uploader = media_client
        oversize = b"x" * (10 * 1024 * 1024 + 1)
        response = await client.post(
            "/api/admin/media",
            files={"file": ("big.png", oversize, "image/png")},
            headers=admin_headers,
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "payload_too_large"
        assert uploader.calls == []

    async def test_oversize_via_content_length_header_is_413_fast_fail(
        self,
        media_client: tuple[AsyncClient, RecordingUploader],
        admin_headers: dict[str, str],
    ) -> None:
        """A forged Content-Length above the 300 MiB router threshold must be
        rejected before the (tiny, actually-sent) body is even read."""
        client, uploader = media_client
        request = client.build_request(
            "POST",
            "/api/admin/media",
            files={"file": ("small.png", b"tiny", "image/png")},
            headers=admin_headers,
        )
        request.headers["content-length"] = str(MAX_UPLOAD_BYTES + 1)
        response = await client.send(request)
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "payload_too_large"
        assert uploader.calls == []


class TestStorageUnset:
    async def test_upload_is_404_when_storage_is_unconfigured(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="no-storage-admin@example.com", role="admin")
        response = await client.post(
            "/api/admin/media",
            files={"file": ("photo.png", b"data", "image/png")},
            headers=auth_headers(admin, test_settings),
        )
        assert response.status_code == 404
