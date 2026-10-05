from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def test_check_returns_located_findings_and_writes_nothing(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b5-check@example.com", role="admin")
    lesson = await create_lesson(
        db_session, await create_module(db_session, await create_track(db_session))
    )
    headers = auth_headers(power, test_settings)
    before = (await client.get(f"/api/lessons/{lesson.id}", headers=headers)).json()

    response = await client.post(
        f"/api/admin/lessons/{lesson.id}/check",
        json={"content_blocks": [{"id": "p", "type": "paragraph", "text": "a — b"}]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["findings"] == [
        {
            "severity": "warning",
            "block_index": 0,
            "where": "block 1 · paragraph",
            "message": "em dash in [0].text",
        }
    ]
    after = (await client.get(f"/api/lessons/{lesson.id}", headers=headers)).json()
    assert after["content_blocks"] == before["content_blocks"]
    assert after["updated_at"] == before["updated_at"]


async def test_check_on_an_unknown_lesson_is_404(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b5-check404@example.com", role="admin")
    response = await client.post(
        f"/api/admin/lessons/{uuid.uuid4()}/check",
        json={"content_blocks": []},
        headers=auth_headers(power, test_settings),
    )
    assert response.status_code == 404
