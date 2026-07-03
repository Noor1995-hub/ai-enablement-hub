"""Learner learning endpoints: graph aggregate, module lessons, lesson detail,
progress upsert (design §3 learning.py + §7 test 5)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest_asyncio

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    assign_module,
    assign_track,
    complete_lesson,
    create_lesson,
    create_module,
    create_prerequisite,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import Lesson, Module, Track, User


@dataclass
class World:
    """Two tracks; track A has two modules (B depends on A1), module A1 has
    three lessons; the learner is assigned track A + module A2 and completed
    lesson 1."""

    track_a: Track
    track_b: Track
    module_a1: Module
    module_a2: Module
    module_b1: Module
    lessons: list[Lesson]
    learner: User


@pytest_asyncio.fixture
async def world(db_session: AsyncSession) -> World:
    track_a = await create_track(db_session, "Track A", sort_order=0, color="#123456")
    track_b = await create_track(db_session, "Track B", sort_order=1, track_type="tool")
    module_a1 = await create_module(db_session, track_a, "A1", sort_order=0)
    module_a2 = await create_module(db_session, track_a, "A2", sort_order=1)
    module_b1 = await create_module(db_session, track_b, "B1", sort_order=0)
    await create_prerequisite(db_session, module_a2, module_a1)
    lessons = [await create_lesson(db_session, module_a1, f"L{i}", sort_order=i) for i in range(3)]
    await create_lesson(db_session, module_a2, "A2-L0", sort_order=0)
    learner = await create_user(db_session, email="graph-learner@example.com")
    await assign_track(db_session, learner, track_a)
    await assign_module(db_session, learner, module_a2)
    await complete_lesson(db_session, learner, lessons[0], {"q1": "answer"})
    return World(track_a, track_b, module_a1, module_a2, module_b1, lessons, learner)


class TestGraph:
    async def test_graph_aggregate_shape_and_counts(
        self, client: AsyncClient, world: World, test_settings: Settings
    ) -> None:
        response = await client.get(
            "/api/learning/graph", headers=auth_headers(world.learner, test_settings)
        )
        assert response.status_code == 200
        graph = response.json()

        tracks = {t["id"]: t for t in graph["tracks"]}
        assert tracks[str(world.track_a.id)]["assigned"] is True
        assert tracks[str(world.track_a.id)]["color"] == "#123456"
        assert tracks[str(world.track_b.id)]["assigned"] is False
        assert tracks[str(world.track_b.id)]["track_type"] == "tool"

        modules = {m["id"]: m for m in graph["modules"]}
        a1 = modules[str(world.module_a1.id)]
        assert a1["lesson_count"] == 3
        assert a1["completed_lesson_count"] == 1
        assert a1["assigned"] is False
        a2 = modules[str(world.module_a2.id)]
        assert a2["assigned"] is True
        assert a2["lesson_count"] == 1
        assert a2["completed_lesson_count"] == 0
        assert modules[str(world.module_b1.id)]["lesson_count"] == 0

        assert graph["prerequisites"] == [
            {
                "module_id": str(world.module_a2.id),
                "prerequisite_module_id": str(world.module_a1.id),
            }
        ]


class TestModuleLessons:
    async def test_lessons_with_completion_and_next(
        self, client: AsyncClient, world: World, test_settings: Settings
    ) -> None:
        response = await client.get(
            f"/api/modules/{world.module_a1.id}/lessons",
            headers=auth_headers(world.learner, test_settings),
        )
        assert response.status_code == 200
        body = response.json()
        assert [lesson["title"] for lesson in body["lessons"]] == ["L0", "L1", "L2"]
        assert [lesson["completed"] for lesson in body["lessons"]] == [True, False, False]
        # First uncompleted lesson.
        assert body["next_lesson_id"] == str(world.lessons[1].id)

    async def test_next_is_null_when_module_fully_completed(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        for lesson in world.lessons[1:]:
            await complete_lesson(db_session, world.learner, lesson)
        response = await client.get(
            f"/api/modules/{world.module_a1.id}/lessons",
            headers=auth_headers(world.learner, test_settings),
        )
        assert response.json()["next_lesson_id"] is None

    async def test_unknown_module_is_404(
        self, client: AsyncClient, world: World, test_settings: Settings
    ) -> None:
        response = await client.get(
            f"/api/modules/{uuid.uuid4()}/lessons",
            headers=auth_headers(world.learner, test_settings),
        )
        assert response.status_code == 404


class TestLessonDetail:
    async def test_detail_aggregates_module_and_answers(
        self, client: AsyncClient, world: World, test_settings: Settings
    ) -> None:
        response = await client.get(
            f"/api/lessons/{world.lessons[0].id}",
            headers=auth_headers(world.learner, test_settings),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["module"] == {
            "id": str(world.module_a1.id),
            "title": "A1",
            "track_id": str(world.track_a.id),
            "sort_order": 0,
        }
        assert body["my_answers"] == {"q1": "answer"}
        # Next lesson within the same module.
        assert body["next_lesson_id"] == str(world.lessons[1].id)
        assert body["next_module_id"] is None

    async def test_my_answers_null_without_progress(
        self, client: AsyncClient, world: World, test_settings: Settings
    ) -> None:
        response = await client.get(
            f"/api/lessons/{world.lessons[1].id}",
            headers=auth_headers(world.learner, test_settings),
        )
        assert response.json()["my_answers"] is None

    async def test_last_lesson_jumps_to_next_module(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """Legacy LessonPage prefetch semantics: last lesson in a module points
        at the first lesson of the next module in the same track."""
        first_a2_lesson = (
            await client.get(
                f"/api/modules/{world.module_a2.id}/lessons",
                headers=auth_headers(world.learner, test_settings),
            )
        ).json()["lessons"][0]
        response = await client.get(
            f"/api/lessons/{world.lessons[2].id}",
            headers=auth_headers(world.learner, test_settings),
        )
        body = response.json()
        assert body["next_module_id"] == str(world.module_a2.id)
        assert body["next_lesson_id"] == first_a2_lesson["id"]

    async def test_end_of_track_has_no_next(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        a2_lessons = (
            await client.get(
                f"/api/modules/{world.module_a2.id}/lessons",
                headers=auth_headers(world.learner, test_settings),
            )
        ).json()["lessons"]
        response = await client.get(
            f"/api/lessons/{a2_lessons[-1]['id']}",
            headers=auth_headers(world.learner, test_settings),
        )
        body = response.json()
        assert body["next_lesson_id"] is None
        assert body["next_module_id"] is None

    async def test_unknown_lesson_is_404(
        self, client: AsyncClient, world: World, test_settings: Settings
    ) -> None:
        response = await client.get(
            f"/api/lessons/{uuid.uuid4()}", headers=auth_headers(world.learner, test_settings)
        )
        assert response.status_code == 404


class TestProgress:
    async def test_upsert_marks_complete_and_stores_answers(
        self, client: AsyncClient, world: World, test_settings: Settings
    ) -> None:
        headers = auth_headers(world.learner, test_settings)
        lesson_id = world.lessons[1].id
        response = await client.put(
            f"/api/lessons/{lesson_id}/progress", json={"answers": {"q": "a"}}, headers=headers
        )
        assert response.status_code == 204
        detail = (await client.get(f"/api/lessons/{lesson_id}", headers=headers)).json()
        assert detail["my_answers"] == {"q": "a"}

    async def test_upsert_is_idempotent_and_updates_answers(
        self, client: AsyncClient, world: World, test_settings: Settings
    ) -> None:
        headers = auth_headers(world.learner, test_settings)
        lesson_id = world.lessons[0].id  # already completed in the fixture
        response = await client.put(
            f"/api/lessons/{lesson_id}/progress",
            json={"answers": {"q1": "revised"}},
            headers=headers,
        )
        assert response.status_code == 204
        detail = (await client.get(f"/api/lessons/{lesson_id}", headers=headers)).json()
        assert detail["my_answers"] == {"q1": "revised"}
        lessons = (
            await client.get(f"/api/modules/{world.module_a1.id}/lessons", headers=headers)
        ).json()["lessons"]
        assert sum(1 for lesson in lessons if lesson["completed"]) == 1

    async def test_null_answers_default_to_empty_dict(
        self, client: AsyncClient, world: World, test_settings: Settings
    ) -> None:
        headers = auth_headers(world.learner, test_settings)
        lesson_id = world.lessons[2].id
        response = await client.put(
            f"/api/lessons/{lesson_id}/progress", json={"answers": None}, headers=headers
        )
        assert response.status_code == 204
        detail = (await client.get(f"/api/lessons/{lesson_id}", headers=headers)).json()
        assert detail["my_answers"] == {}

    async def test_unknown_lesson_is_404(
        self, client: AsyncClient, world: World, test_settings: Settings
    ) -> None:
        response = await client.put(
            f"/api/lessons/{uuid.uuid4()}/progress",
            json={"answers": {}},
            headers=auth_headers(world.learner, test_settings),
        )
        assert response.status_code == 404
