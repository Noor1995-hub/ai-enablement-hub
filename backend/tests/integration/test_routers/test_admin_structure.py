"""B4 endpoints end to end (spec 2026-10-05). Rules are pinned in
tests/unit/test_content_structure_service.py and test_assignment_gap.py; here:
wiring, status codes, the cascade, and project isolation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.assignment_repository import AssignmentRepository
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    assign_lesson,
    assign_module,
    complete_lesson,
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_track,
    create_user,
    make_project_admin,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


async def test_tree_lists_modules_with_prerequisites_and_lessons(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b4-tree-power@example.com", role="admin")
    track = await create_track(db_session, "B4 Tree")
    first = await create_module(db_session, track, "First")
    second = await create_module(db_session, track, "Second")
    await create_lesson(db_session, second, "Only")
    headers = auth_headers(power, test_settings)
    await client.put(
        f"/api/admin/modules/{second.id}/prerequisites",
        json={"prerequisite_ids": [str(first.id)]},
        headers=headers,
    )

    response = await client.get("/api/admin/content/tree", headers=headers)

    assert response.status_code == 200
    ours = next(t for t in response.json()["tracks"] if t["id"] == str(track.id))
    assert [m["title"] for m in ours["modules"]] == ["First", "Second"]
    assert ours["modules"][1]["prerequisite_ids"] == [str(first.id)]
    assert [le["title"] for le in ours["modules"][1]["lessons"]] == ["Only"]


async def test_a_prerequisite_cycle_is_400(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b4-cycle-power@example.com", role="admin")
    track = await create_track(db_session)
    a = await create_module(db_session, track, "Alpha")
    b = await create_module(db_session, track, "Beta")
    headers = auth_headers(power, test_settings)
    ok = await client.put(
        f"/api/admin/modules/{b.id}/prerequisites",
        json={"prerequisite_ids": [str(a.id)]},
        headers=headers,
    )
    assert ok.status_code == 204

    loop = await client.put(
        f"/api/admin/modules/{a.id}/prerequisites",
        json={"prerequisite_ids": [str(b.id)]},
        headers=headers,
    )

    assert loop.status_code == 400
    assert "Alpha" in loop.json()["error"]["message"]


async def test_track_delete_impact_then_cascade(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b4-del-power@example.com", role="admin")
    learner = await create_user(db_session, email="b4-del-learner@example.com")
    track = await create_track(db_session, "Doomed")
    module = await create_module(db_session, track)
    lesson = await create_lesson(db_session, module)
    await assign_lesson(db_session, learner, lesson)
    await complete_lesson(db_session, learner, lesson)
    headers = auth_headers(power, test_settings)

    impact = await client.get(f"/api/admin/tracks/{track.id}/impact", headers=headers)
    assert impact.json() == {
        "modules": 1,
        "lessons": 1,
        "learners_assigned": 1,
        "learners_with_progress": 1,
    }

    deleted = await client.delete(f"/api/admin/tracks/{track.id}", headers=headers)
    assert deleted.status_code == 204
    gone = await client.get(f"/api/modules/{module.id}/lessons", headers=headers)
    assert gone.status_code == 404


async def test_move_module_and_lesson(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b4-move-power@example.com", role="admin")
    source = await create_track(db_session, "Src")
    dest = await create_track(db_session, "Dst")
    module = await create_module(db_session, source, "Mover")
    target = await create_module(db_session, dest, "Target")
    lesson = await create_lesson(db_session, module, "Traveller")
    headers = auth_headers(power, test_settings)

    moved = await client.patch(
        f"/api/admin/modules/{module.id}", json={"track_id": str(dest.id)}, headers=headers
    )
    assert moved.status_code == 200
    assert moved.json()["track_id"] == str(dest.id)
    assert moved.json()["sort_order"] == 1

    lesson_moved = await client.patch(
        f"/api/admin/lessons/{lesson.id}", json={"module_id": str(target.id)}, headers=headers
    )
    assert lesson_moved.status_code == 200
    assert lesson_moved.json()["module_id"] == str(target.id)


async def test_reorder_with_a_wrong_set_is_400(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b4-order-power@example.com", role="admin")
    track = await create_track(db_session)
    a = await create_module(db_session, track, "A")
    await create_module(db_session, track, "B")

    response = await client.put(
        f"/api/admin/tracks/{track.id}/modules/order",
        json={"module_ids": [str(a.id)]},
        headers=auth_headers(power, test_settings),
    )

    assert response.status_code == 400


async def test_project_assign_never_touches_another_project(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    company = await create_company(db_session, "B4 Co")
    ours = await create_project(db_session, company, "B4 Ours")
    theirs = await create_project(db_session, company, "B4 Theirs")
    coach = await create_user(
        db_session, email="b4-coach@example.com", password="hunter2hunter2", project_id=theirs.id
    )
    await make_project_admin(db_session, coach, ours)
    mine = await create_user(db_session, email="b4-mine@example.com", project_id=ours.id)
    other = await create_user(db_session, email="b4-other@example.com", project_id=theirs.id)
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    old = await create_lesson(db_session, module, "Old", sort_order=0)
    for user in (mine, other):
        await assign_module(db_session, user, module)
        await assign_lesson(db_session, user, old)
    new = await create_lesson(db_session, module, "New", sort_order=1)
    headers = auth_headers(coach, test_settings)
    base = f"/api/admin/projects/{ours.id}/modules/{module.id}"

    gap = await client.get(f"{base}/assignment-gap", headers=headers)
    assert gap.json() == {"lesson_ids": [str(new.id)], "learner_count": 1, "missing_pairs": 1}

    assigned = await client.post(f"{base}/assign-new-lessons", headers=headers)
    assert assigned.json() == {"assigned_pairs": 1}
    repo = AssignmentRepository(db_session)
    assert new.id in await repo.lesson_ids_for_user(mine.id)
    assert new.id not in await repo.lesson_ids_for_user(other.id)

    foreign = await client.get(
        f"/api/admin/projects/{theirs.id}/modules/{module.id}/assignment-gap", headers=headers
    )
    assert foreign.status_code == 404


async def test_explicit_null_on_a_required_field_is_422(
    client: AsyncClient, db_session: AsyncSession, test_settings: Settings
) -> None:
    power = await create_user(db_session, email="b4-null-power@example.com", role="admin")
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    headers = auth_headers(power, test_settings)

    for body in ({"name": None}, {"track_type": None}, {"required_level": None}):
        response = await client.patch(f"/api/admin/tracks/{track.id}", json=body, headers=headers)
        assert response.status_code == 422, body
    response = await client.patch(
        f"/api/admin/modules/{module.id}", json={"title": None}, headers=headers
    )
    assert response.status_code == 422
    cleared = await client.patch(
        f"/api/admin/tracks/{track.id}", json={"color": None}, headers=headers
    )
    assert cleared.status_code == 200
