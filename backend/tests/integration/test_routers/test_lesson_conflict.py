"""No silent overwrites (B5): PATCH /api/admin/lessons/{id} with expected_updated_at."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def _setup(db_session: AsyncSession):  # noqa: ANN202
    a = await create_user(
        db_session, email="b5-a@example.com", role="admin", first_name="Ann", last_name="Admin"
    )
    b = await create_user(
        db_session, email="b5-b@example.com", role="admin", first_name="Bob", last_name="Boss"
    )
    lesson = await create_lesson(
        db_session, await create_module(db_session, await create_track(db_session))
    )
    return a, b, lesson


async def test_a_save_from_an_outdated_copy_is_409_with_who_and_when(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    a, b, lesson = await _setup(db_session)
    base = (
        await client.get(f"/api/lessons/{lesson.id}", headers=auth_headers(a, test_settings))
    ).json()["updated_at"]

    first = await client.patch(
        f"/api/admin/lessons/{lesson.id}",
        json={"title": "Bob's edit", "expected_updated_at": base},
        headers=auth_headers(b, test_settings),
    )
    assert first.status_code == 200

    stale = await client.patch(
        f"/api/admin/lessons/{lesson.id}",
        json={"title": "Ann's edit", "expected_updated_at": base},
        headers=auth_headers(a, test_settings),
    )
    assert stale.status_code == 409
    error = stale.json()["error"]
    assert error["code"] == "lesson_changed"
    assert error["updated_by_name"] == "Bob Boss"
    assert error["updated_at"] == first.json()["updated_at"]


async def test_saved_updated_at_round_trips_into_the_next_save(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    a, _, lesson = await _setup(db_session)
    headers = auth_headers(a, test_settings)
    base = (await client.get(f"/api/lessons/{lesson.id}", headers=headers)).json()["updated_at"]
    one = await client.patch(
        f"/api/admin/lessons/{lesson.id}",
        json={"title": "One", "expected_updated_at": base},
        headers=headers,
    )
    two = await client.patch(
        f"/api/admin/lessons/{lesson.id}",
        json={"title": "Two", "expected_updated_at": one.json()["updated_at"]},
        headers=headers,
    )
    assert two.status_code == 200


async def test_an_omitted_expected_updated_at_still_saves(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    a, _, lesson = await _setup(db_session)
    response = await client.patch(
        f"/api/admin/lessons/{lesson.id}",
        json={"title": "Old client"},
        headers=auth_headers(a, test_settings),
    )
    assert response.status_code == 200


async def test_a_reorder_does_not_stamp(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    a, _, lesson = await _setup(db_session)
    headers = auth_headers(a, test_settings)
    before = (await client.get(f"/api/lessons/{lesson.id}", headers=headers)).json()["updated_at"]
    await client.put(
        f"/api/admin/modules/{lesson.module_id}/lessons/order",
        json={"lesson_ids": [str(lesson.id)]},
        headers=headers,
    )
    after = (await client.get(f"/api/lessons/{lesson.id}", headers=headers)).json()["updated_at"]
    assert after == before
