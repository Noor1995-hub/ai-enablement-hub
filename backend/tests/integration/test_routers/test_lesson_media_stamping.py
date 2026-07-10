"""Lesson-media read/write boundary (design B3): GET /api/lessons/{id} stamps
fresh SAS urls onto image/blob-video blocks; PATCH /api/admin/lessons/{id}
strips ephemeral urls before persisting and stamps its own response. Covers
the configured-storage matrix, the storage-unset passthrough, and the
DB-stays-clean guarantee (a fresh `session.refresh` forces a real SELECT, so
a bug that mutated the ORM's JSONB attribute in place would surface here)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.dependencies.database import get_session
from src.core.dependencies.settings import get_settings
from src.core.dependencies.storage import get_media_service
from src.main import app
from src.services.media_service import MediaService
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user
from tests.fixtures.media import TEST_STORAGE, RecordingUploader

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings

IMAGE_BLOCK: dict[str, Any] = {
    "id": "b1",
    "type": "image",
    "blob_path": "images/abc.png",
    "alt": "A picture",
}
VIDEO_BLOB_BLOCK: dict[str, Any] = {
    "id": "b2",
    "type": "video",
    "source": "blob",
    "blob_path": "videos/def.mp4",
}
VIDEO_EMBED_BLOCK: dict[str, Any] = {
    "id": "b3",
    "type": "video",
    "source": "embed",
    "url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
}
UNKNOWN_BLOCK: dict[str, Any] = {"id": "b4", "type": "callout", "text": "A note"}

_SAS_PREFIX = f"{TEST_STORAGE.blob_endpoint}/{TEST_STORAGE.container}"


@pytest_asyncio.fixture
async def media_client(
    db_session: AsyncSession, test_settings: Settings
) -> AsyncGenerator[AsyncClient]:
    """conftest's client plus a real MediaService (SAS math is real, offline
    HMAC) so GET/PATCH stamping runs end to end (mirrors test_admin_media.py's
    media_client)."""
    service = MediaService(
        RecordingUploader(),
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
        yield client
    finally:
        await client.aclose()
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_headers(db_session: AsyncSession, test_settings: Settings) -> dict[str, str]:
    admin = await create_user(db_session, email="media-stamp-admin@example.com", role="admin")
    return auth_headers(admin, test_settings)


class TestGetLessonStamping:
    async def test_stamps_image_and_blob_video_leaves_embed_and_db_clean(
        self,
        media_client: AsyncClient,
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        track = await create_track(db_session, "Media Track")
        module = await create_module(db_session, track, "Media Module")
        original_blocks = [IMAGE_BLOCK, VIDEO_BLOB_BLOCK, VIDEO_EMBED_BLOCK]
        lesson = await create_lesson(
            db_session, module, "Media Lesson", content_blocks=original_blocks
        )
        learner = await create_user(db_session, email="media-learner@example.com")

        response = await media_client.get(
            f"/api/lessons/{lesson.id}", headers=auth_headers(learner, test_settings)
        )

        assert response.status_code == 200
        image, video_blob, video_embed = response.json()["content_blocks"]
        assert image["url"].startswith(f"{_SAS_PREFIX}/images/abc.png?")
        assert video_blob["url"].startswith(f"{_SAS_PREFIX}/videos/def.mp4?")
        assert video_embed["url"] == VIDEO_EMBED_BLOCK["url"]

        # Force a real SELECT (not the in-memory identity-mapped object): a
        # bug that assigned the stamped list onto the ORM attribute would
        # also mark it dirty and get autoflushed here, so this would catch it.
        await db_session.refresh(lesson)
        assert lesson.content_blocks == original_blocks

    async def test_unassigned_learner_still_gets_stamped_urls(
        self,
        media_client: AsyncClient,
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        """Stamping doesn't depend on progress/assignment state — same lesson
        row, just confirming the media dependency runs on the plain path too."""
        track = await create_track(db_session, "Media Track 2")
        module = await create_module(db_session, track, "Media Module 2")
        lesson = await create_lesson(
            db_session, module, "Media Lesson 2", content_blocks=[IMAGE_BLOCK]
        )
        learner = await create_user(db_session, email="media-learner-2@example.com")

        response = await media_client.get(
            f"/api/lessons/{lesson.id}", headers=auth_headers(learner, test_settings)
        )
        assert response.status_code == 200
        assert response.json()["content_blocks"][0]["url"].startswith(
            f"{_SAS_PREFIX}/images/abc.png?"
        )


class TestPatchLessonStamping:
    async def test_patch_strips_on_write_but_stamps_the_response(
        self,
        media_client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict[str, str],
    ) -> None:
        track = await create_track(db_session, "Patch Media Track")
        module = await create_module(db_session, track, "Patch Media Module")
        lesson = await create_lesson(db_session, module, "Draft")

        # Simulate the editor echoing back previously-stamped (now stale)
        # urls verbatim.
        stale_image = {**IMAGE_BLOCK, "url": f"{_SAS_PREFIX}/images/abc.png?sig=STALE"}
        stale_video_blob = {
            **VIDEO_BLOB_BLOCK,
            "url": f"{_SAS_PREFIX}/videos/def.mp4?sig=STALE",
        }
        payload_blocks = [stale_image, stale_video_blob, VIDEO_EMBED_BLOCK]

        response = await media_client.patch(
            f"/api/admin/lessons/{lesson.id}",
            json={"content_blocks": payload_blocks},
            headers=admin_headers,
        )

        assert response.status_code == 200
        image, video_blob, video_embed = response.json()["content_blocks"]
        assert image["url"].startswith(f"{_SAS_PREFIX}/images/abc.png?")
        assert "STALE" not in image["url"]
        assert video_blob["url"].startswith(f"{_SAS_PREFIX}/videos/def.mp4?")
        assert "STALE" not in video_blob["url"]
        assert video_embed["url"] == VIDEO_EMBED_BLOCK["url"]

        await db_session.refresh(lesson)
        persisted_image, persisted_video_blob, persisted_video_embed = lesson.content_blocks
        assert "url" not in persisted_image
        assert persisted_image["blob_path"] == IMAGE_BLOCK["blob_path"]
        assert "url" not in persisted_video_blob
        assert persisted_video_blob["blob_path"] == VIDEO_BLOB_BLOCK["blob_path"]
        assert persisted_video_embed["url"] == VIDEO_EMBED_BLOCK["url"]

    async def test_patch_strips_regardless_of_block_shape_mdx_editor_path(
        self,
        media_client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict[str, str],
    ) -> None:
        """The block editor and the raw-MDX editor both save through this one
        PATCH endpoint/service method (no separate branch in the backend) — a
        differently-shaped payload (a freeform markdown block alongside an
        image block) must still be stripped before it is persisted."""
        track = await create_track(db_session, "MDX Track")
        module = await create_module(db_session, track, "MDX Module")
        lesson = await create_lesson(db_session, module, "MDX Draft")

        mdx_blocks = [
            {"id": "m1", "type": "markdown", "body": "# Heading\n\nSome *mdx* text."},
            {**IMAGE_BLOCK, "url": f"{_SAS_PREFIX}/images/abc.png?sig=STALE"},
        ]

        response = await media_client.patch(
            f"/api/admin/lessons/{lesson.id}",
            json={"content_blocks": mdx_blocks},
            headers=admin_headers,
        )
        assert response.status_code == 200

        await db_session.refresh(lesson)
        markdown_block, image_block = lesson.content_blocks
        assert markdown_block == mdx_blocks[0]
        assert "url" not in image_block

    async def test_patch_title_only_leaves_content_blocks_untouched_and_stamped(
        self,
        media_client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict[str, str],
    ) -> None:
        track = await create_track(db_session, "Partial Patch Track")
        module = await create_module(db_session, track, "Partial Patch Module")
        lesson = await create_lesson(db_session, module, "Draft", content_blocks=[IMAGE_BLOCK])

        response = await media_client.patch(
            f"/api/admin/lessons/{lesson.id}",
            json={"title": "Renamed"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["content_blocks"][0]["url"].startswith(
            f"{_SAS_PREFIX}/images/abc.png?"
        )

        await db_session.refresh(lesson)
        assert "url" not in lesson.content_blocks[0]


class TestStorageUnset:
    async def test_get_lesson_passes_blocks_through_unchanged(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        track = await create_track(db_session, "No Storage Track")
        module = await create_module(db_session, track, "No Storage Module")
        original_blocks = [IMAGE_BLOCK, VIDEO_BLOB_BLOCK, VIDEO_EMBED_BLOCK]
        lesson = await create_lesson(
            db_session, module, "No Storage Lesson", content_blocks=original_blocks
        )
        learner = await create_user(db_session, email="no-storage-learner@example.com")

        response = await client.get(
            f"/api/lessons/{lesson.id}", headers=auth_headers(learner, test_settings)
        )
        assert response.status_code == 200
        assert response.json()["content_blocks"] == original_blocks

    async def test_patch_still_strips_ephemeral_urls(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(
            db_session, email="no-storage-patch-admin@example.com", role="admin"
        )
        track = await create_track(db_session, "No Storage Patch Track")
        module = await create_module(db_session, track, "No Storage Patch Module")
        lesson = await create_lesson(db_session, module, "Draft")

        stale_image = {**IMAGE_BLOCK, "url": "https://stale.example.com/images/abc.png?sig=OLD"}
        response = await client.patch(
            f"/api/admin/lessons/{lesson.id}",
            json={"content_blocks": [stale_image, VIDEO_EMBED_BLOCK]},
            headers=auth_headers(admin, test_settings),
        )

        assert response.status_code == 200
        image, video_embed = response.json()["content_blocks"]
        assert "url" not in image
        assert video_embed["url"] == VIDEO_EMBED_BLOCK["url"]

        await db_session.refresh(lesson)
        persisted_image, persisted_video_embed = lesson.content_blocks
        assert "url" not in persisted_image
        assert persisted_video_embed["url"] == VIDEO_EMBED_BLOCK["url"]


class TestUnknownBlockRoundTrip:
    async def test_unknown_block_survives_get_and_patch_unchanged(
        self,
        media_client: AsyncClient,
        db_session: AsyncSession,
        test_settings: Settings,
        admin_headers: dict[str, str],
    ) -> None:
        track = await create_track(db_session, "Unknown Block Track")
        module = await create_module(db_session, track, "Unknown Block Module")
        lesson = await create_lesson(
            db_session, module, "Unknown Block Lesson", content_blocks=[UNKNOWN_BLOCK]
        )
        learner = await create_user(db_session, email="unknown-block-learner@example.com")

        get_response = await media_client.get(
            f"/api/lessons/{lesson.id}", headers=auth_headers(learner, test_settings)
        )
        assert get_response.status_code == 200
        assert get_response.json()["content_blocks"] == [UNKNOWN_BLOCK]

        patch_response = await media_client.patch(
            f"/api/admin/lessons/{lesson.id}",
            json={"content_blocks": [UNKNOWN_BLOCK]},
            headers=admin_headers,
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["content_blocks"] == [UNKNOWN_BLOCK]

        await db_session.refresh(lesson)
        assert lesson.content_blocks == [UNKNOWN_BLOCK]
