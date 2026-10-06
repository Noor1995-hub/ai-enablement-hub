"""GET/DELETE /api/admin/media (B6) with the storage faked (pattern of test_admin_media.py)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import TYPE_CHECKING

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
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings

USED = "images/" + "a" * 32 + ".png"
UNUSED = "images/" + "b" * 32 + ".png"


@pytest_asyncio.fixture
async def library(
    db_session: AsyncSession, test_settings: Settings
) -> AsyncGenerator[tuple[AsyncClient, RecordingUploader]]:
    uploader = RecordingUploader()
    uploader.stored[USED] = (100, datetime(2026, 1, 1, tzinfo=UTC))
    uploader.stored[UNUSED] = (50, datetime(2026, 2, 1, tzinfo=UTC))
    service = MediaService(
        uploader,
        account_name=TEST_STORAGE.account_name,
        account_key=TEST_STORAGE.account_key.get_secret_value(),
        blob_endpoint=TEST_STORAGE.blob_endpoint,
        container=TEST_STORAGE.container,
        sas_ttl_hours=TEST_STORAGE.sas_ttl_hours,
    )

    async def _session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_media_service] = lambda: service
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    try:
        yield client, uploader
    finally:
        await client.aclose()
        app.dependency_overrides.clear()


async def test_list_shows_usage_and_totals(
    library: tuple[AsyncClient, RecordingUploader],
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    client, _ = library
    power = await create_user(db_session, email="b6-media-list@example.com", role="admin")
    module = await create_module(db_session, await create_track(db_session), "B6 Media Module")
    lesson = await create_lesson(
        db_session,
        module,
        "B6 Media Lesson",
        content_blocks=[{"id": "i", "type": "image", "blob_path": USED, "alt": "a"}],
    )

    response = await client.get("/api/admin/media", headers=auth_headers(power, test_settings))

    assert response.status_code == 200
    body = response.json()
    assert body["total_bytes"] == 150
    by_path = {f["path"]: f for f in body["files"]}
    assert by_path[USED]["used_in"] == [
        {
            "lesson_id": str(lesson.id),
            "lesson_title": "B6 Media Lesson",
            "module_title": "B6 Media Module",
        }
    ]
    assert by_path[UNUSED]["used_in"] == []
    assert by_path[UNUSED]["preview_url"]


async def test_delete_unused_used_and_malformed(
    library: tuple[AsyncClient, RecordingUploader],
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    client, uploader = library
    power = await create_user(db_session, email="b6-media-del@example.com", role="admin")
    module = await create_module(db_session, await create_track(db_session))
    await create_lesson(
        db_session,
        module,
        "Uses it",
        content_blocks=[{"id": "i", "type": "image", "blob_path": USED, "alt": "a"}],
    )
    headers = auth_headers(power, test_settings)

    ok = await client.delete(f"/api/admin/media/{UNUSED}", headers=headers)
    assert ok.status_code == 204
    assert uploader.deleted == [UNUSED]

    used = await client.delete(f"/api/admin/media/{USED}", headers=headers)
    assert used.status_code == 409
    assert "Uses it" in used.json()["error"]["message"]

    for bad in ("/api/admin/media/docs/" + "c" * 32 + ".png", "/api/admin/media/images/x.png"):
        assert (await client.delete(bad, headers=headers)).status_code == 404
