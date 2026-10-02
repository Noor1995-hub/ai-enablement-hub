"""Learner learning endpoints: graph aggregate, module lessons, lesson detail,
progress upsert (design §3 learning.py + §7 test 5)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.engine import Connection

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    assign_lesson,
    assign_module,
    assign_track,
    complete_lesson,
    create_company,
    create_lesson,
    create_module,
    create_prerequisite,
    create_project,
    create_survey,
    create_track,
    create_user,
    unlock_component,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import Lesson, Module, Track, User


@dataclass
class World:
    """Two tracks; track A has two modules (B depends on A1), module A1 has
    three lessons; the learner is assigned track A + module A2, ALL lessons
    (backfill parity), and completed lesson 1."""

    track_a: Track
    track_b: Track
    module_a1: Module
    module_a2: Module
    module_b1: Module
    lessons: list[Lesson]
    lesson_a2: Lesson
    learner: User
    project_id: uuid.UUID


@pytest_asyncio.fixture
async def world(db_session: AsyncSession) -> World:
    company = await create_company(db_session, "Learning World Co")
    project = await create_project(db_session, company, "Learning World Project")
    await unlock_component(db_session, project, "learning")
    track_a = await create_track(db_session, "Track A", sort_order=0, color="#123456")
    track_b = await create_track(db_session, "Track B", sort_order=1, track_type="tool")
    module_a1 = await create_module(db_session, track_a, "A1", sort_order=0)
    module_a2 = await create_module(db_session, track_a, "A2", sort_order=1)
    module_b1 = await create_module(db_session, track_b, "B1", sort_order=0)
    await create_prerequisite(db_session, module_a2, module_a1)
    lessons = [await create_lesson(db_session, module_a1, f"L{i}", sort_order=i) for i in range(3)]
    lesson_a2 = await create_lesson(db_session, module_a2, "A2-L0", sort_order=0)
    learner = await create_user(
        db_session, email="graph-learner@example.com", project_id=project.id
    )
    await assign_track(db_session, learner, track_a)
    await assign_module(db_session, learner, module_a2)
    for lesson in [*lessons, lesson_a2]:
        await assign_lesson(db_session, learner, lesson)
    await complete_lesson(db_session, learner, lessons[0], {"q1": "answer"})
    return World(
        track_a, track_b, module_a1, module_a2, module_b1, lessons, lesson_a2, learner, project.id
    )


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

    async def test_counts_only_cover_assigned_lessons(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """lesson_count is the caller's curriculum, not the module inventory;
        completed lessons that are not assigned do not count either."""
        partial = await create_user(
            db_session, email="partial-learner@example.com", project_id=world.project_id
        )
        await assign_track(db_session, partial, world.track_a)
        await assign_module(db_session, partial, world.module_a1)
        await assign_lesson(db_session, partial, world.lessons[0])
        await assign_lesson(db_session, partial, world.lessons[1])
        await complete_lesson(db_session, partial, world.lessons[0])
        await complete_lesson(db_session, partial, world.lessons[2])  # NOT assigned

        graph = (
            await client.get("/api/learning/graph", headers=auth_headers(partial, test_settings))
        ).json()
        a1 = next(m for m in graph["modules"] if m["id"] == str(world.module_a1.id))
        assert a1["lesson_count"] == 2
        assert a1["completed_lesson_count"] == 1

    async def test_graph_does_not_run_its_shared_reads_twice(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """/learning/graph used to compute maturity and the graph independently, so
        list_tracks / list_modules / assigned_lesson_counts_by_module each ran twice
        per request. A learner with no survey/override short-circuits effective_level
        before any read, so give this one a completed survey first — otherwise the
        duplication never happens and this test would pass even unfixed."""
        await create_survey(db_session, world.learner, status="complete", score_level="explore")

        seen: list[str] = []

        def _record(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
            seen.append(" ".join(statement.split()))

        bind = db_session.get_bind()
        assert isinstance(bind, Connection)
        event.listen(bind, "before_cursor_execute", _record)
        try:
            response = await client.get(
                "/api/learning/graph", headers=auth_headers(world.learner, test_settings)
            )
        finally:
            event.remove(bind, "before_cursor_execute", _record)

        assert response.status_code == 200
        tracks_selects = [s for s in seen if s.startswith("SELECT tracks.")]
        modules_selects = [s for s in seen if s.startswith("SELECT modules.")]
        assert len(tracks_selects) == 1, f"tracks read {len(tracks_selects)}x: {tracks_selects}"
        assert len(modules_selects) == 1, f"modules read {len(modules_selects)}x: {modules_selects}"


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
        assert [lesson["assigned"] for lesson in body["lessons"]] == [True, True, True]
        # First uncompleted assigned lesson.
        assert body["next_lesson_id"] == str(world.lessons[1].id)

    async def test_all_lessons_returned_with_flags_and_next_skips_unassigned(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """ALL lessons come back (the admin ModulePanel uses this endpoint);
        `assigned` is per-caller and next skips unassigned lessons."""
        partial = await create_user(
            db_session, email="partial-lessons@example.com", project_id=world.project_id
        )
        await assign_lesson(db_session, partial, world.lessons[0])
        await assign_lesson(db_session, partial, world.lessons[2])
        await complete_lesson(db_session, partial, world.lessons[0])

        body = (
            await client.get(
                f"/api/modules/{world.module_a1.id}/lessons",
                headers=auth_headers(partial, test_settings),
            )
        ).json()
        assert [lesson["assigned"] for lesson in body["lessons"]] == [True, False, True]
        assert body["next_lesson_id"] == str(world.lessons[2].id)

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

    async def test_next_skips_unassigned_lessons(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        partial = await create_user(
            db_session, email="partial-detail@example.com", project_id=world.project_id
        )
        await assign_lesson(db_session, partial, world.lessons[0])
        await assign_lesson(db_session, partial, world.lessons[2])

        body = (
            await client.get(
                f"/api/lessons/{world.lessons[0].id}",
                headers=auth_headers(partial, test_settings),
            )
        ).json()
        assert body["next_lesson_id"] == str(world.lessons[2].id)
        assert body["next_module_id"] is None

    async def test_cross_module_hop_requires_assigned_lesson(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """The hop still names the next module, but with none of its lessons
        assigned there is no next lesson to land on."""
        partial = await create_user(
            db_session, email="partial-hop@example.com", project_id=world.project_id
        )
        await assign_lesson(db_session, partial, world.lessons[2])

        body = (
            await client.get(
                f"/api/lessons/{world.lessons[2].id}",
                headers=auth_headers(partial, test_settings),
            )
        ).json()
        assert body["next_module_id"] == str(world.module_a2.id)
        assert body["next_lesson_id"] is None

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


class TestLessonAccessControl:
    """Assignment + maturity are now access control on the two lesson endpoints,
    not just visibility filters. Prerequisite ordering is deliberately NOT
    enforced server-side (see the plan's decision note)."""

    async def test_unassigned_above_level_lesson_is_403(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        locked_track = await create_track(
            db_session, "Locked Track", sort_order=9, required_level="integrator"
        )
        locked_module = await create_module(db_session, locked_track, "Locked Module")
        locked_lesson = await create_lesson(db_session, locked_module, "Locked Lesson")

        response = await client.get(
            f"/api/lessons/{locked_lesson.id}",
            headers=auth_headers(world.learner, test_settings),
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_progress_on_an_inaccessible_lesson_is_403(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        locked_track = await create_track(
            db_session, "Locked Progress Track", sort_order=10, required_level="integrator"
        )
        locked_module = await create_module(db_session, locked_track, "Locked Progress Module")
        locked_lesson = await create_lesson(db_session, locked_module, "Locked Progress Lesson")

        response = await client.put(
            f"/api/lessons/{locked_lesson.id}/progress",
            json={"answers": {}},
            headers=auth_headers(world.learner, test_settings),
        )
        assert response.status_code == 403

    async def test_assessed_learner_is_gated_by_level_not_just_by_survey(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """A learner WITH a completed assessment (effective level practitioner;
        nothing assigned, so no live progression) is refused an unassigned lesson
        on a track above their level, and allowed unassigned lessons at and
        below it, on both endpoints."""
        assessed = await create_user(
            db_session, email="assessed-practitioner@example.com", project_id=world.project_id
        )
        await create_survey(db_session, assessed, status="complete", score_level="practitioner")
        lessons_by_level: dict[str, Lesson] = {}
        for offset, level in enumerate(("explore", "practitioner", "integrator")):
            track = await create_track(
                db_session, f"Level {level} Track", sort_order=20 + offset, required_level=level
            )
            module = await create_module(db_session, track, f"Level {level} Module")
            lessons_by_level[level] = await create_lesson(
                db_session, module, f"Level {level} Lesson"
            )
        headers = auth_headers(assessed, test_settings)

        above = lessons_by_level["integrator"]
        assert (await client.get(f"/api/lessons/{above.id}", headers=headers)).status_code == 403
        put_above = await client.put(
            f"/api/lessons/{above.id}/progress", json={"answers": {}}, headers=headers
        )
        assert put_above.status_code == 403

        for level in ("practitioner", "explore"):
            lesson = lessons_by_level[level]
            got = await client.get(f"/api/lessons/{lesson.id}", headers=headers)
            assert got.status_code == 200, level
            put = await client.put(
                f"/api/lessons/{lesson.id}/progress", json={"answers": {}}, headers=headers
            )
            assert put.status_code == 204, level

    async def test_assignment_alone_grants_access_even_above_level(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """An assignment is an admin's explicit grant; a maturity computation
        must never lock a learner out of content they were given."""
        high_track = await create_track(
            db_session, "Granted Track", sort_order=11, required_level="multiplier"
        )
        high_module = await create_module(db_session, high_track, "Granted Module")
        high_lesson = await create_lesson(db_session, high_module, "Granted Lesson")
        await assign_lesson(db_session, world.learner, high_lesson)
        headers = auth_headers(world.learner, test_settings)

        response = await client.get(f"/api/lessons/{high_lesson.id}", headers=headers)
        assert response.status_code == 200
        put = await client.put(
            f"/api/lessons/{high_lesson.id}/progress", json={"answers": {}}, headers=headers
        )
        assert put.status_code == 204

    async def test_maturity_alone_grants_access_to_an_unassigned_lesson(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """Below-/at-level free review is a shipped feature (2026-07-20): the
        API must not 403 what the learning path lets them click."""
        explorer = await create_user(
            db_session, email="explorer-browser@example.com", project_id=world.project_id
        )
        await create_survey(db_session, explorer, status="complete", score_level="explore")
        open_track = await create_track(
            db_session, "Open Track", sort_order=12, required_level="explore"
        )
        open_module = await create_module(db_session, open_track, "Open Module")
        open_lesson = await create_lesson(db_session, open_module, "Open Lesson")

        response = await client.get(
            f"/api/lessons/{open_lesson.id}", headers=auth_headers(explorer, test_settings)
        )
        assert response.status_code == 200

    async def test_introduction_lessons_need_no_assignment(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        intro_track = await create_track(
            db_session, "Intro Access Track", sort_order=13, is_introduction=True
        )
        intro_module = await create_module(db_session, intro_track, "Intro Access Module")
        intro_lesson = await create_lesson(db_session, intro_module, "Intro Access Lesson")
        newcomer = await create_user(
            db_session, email="intro-newcomer@example.com", project_id=world.project_id
        )
        headers = auth_headers(newcomer, test_settings)

        response = await client.get(f"/api/lessons/{intro_lesson.id}", headers=headers)
        assert response.status_code == 200
        put = await client.put(
            f"/api/lessons/{intro_lesson.id}/progress", json={"answers": {}}, headers=headers
        )
        assert put.status_code == 204

    async def test_admin_bypasses_the_gate(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        locked_track = await create_track(
            db_session, "Bypass Track", sort_order=14, required_level="multiplier"
        )
        locked_module = await create_module(db_session, locked_track, "Bypass Module")
        locked_lesson = await create_lesson(db_session, locked_module, "Bypass Lesson")
        admin = await create_user(
            db_session,
            email="bypass-admin@example.com",
            role="admin",
            project_id=world.project_id,
        )

        response = await client.get(
            f"/api/lessons/{locked_lesson.id}", headers=auth_headers(admin, test_settings)
        )
        assert response.status_code == 200

    async def test_unknown_lesson_is_still_404_not_403(
        self, client: AsyncClient, world: World, test_settings: Settings
    ) -> None:
        """Existence is checked before access, so a deleted lesson keeps 404ing
        (test_admin_content.py's delete test depends on this)."""
        response = await client.get(
            f"/api/lessons/{uuid.uuid4()}", headers=auth_headers(world.learner, test_settings)
        )
        assert response.status_code == 404

    async def test_module_lessons_listing_is_not_gated(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """The listing endpoint stays the discovery surface: it already returns
        per-caller `assigned` flags and the UI filters on them."""
        locked_track = await create_track(
            db_session, "Listing Track", sort_order=15, required_level="integrator"
        )
        locked_module = await create_module(db_session, locked_track, "Listing Module")
        await create_lesson(db_session, locked_module, "Listing Lesson")

        response = await client.get(
            f"/api/modules/{locked_module.id}/lessons",
            headers=auth_headers(world.learner, test_settings),
        )
        assert response.status_code == 200


class TestScopedAssignmentsAndTotalOrder:
    """lesson_ids_for_user takes an optional candidate set so a caller testing
    one module's membership does not read every lesson the user owns; "next
    lesson" follows list_lessons' (sort_order, id) total order."""

    async def test_lesson_ids_for_user_can_be_scoped_to_a_candidate_set(
        self, world: World, db_session: AsyncSession
    ) -> None:
        from src.repositories.assignment_repository import AssignmentRepository

        track = await create_track(db_session, "Scope Track", sort_order=30)
        module = await create_module(db_session, track, "Scope Module")
        wanted = await create_lesson(db_session, module, "Wanted", sort_order=0)
        other = await create_lesson(db_session, module, "Other", sort_order=1)
        await assign_lesson(db_session, world.learner, wanted)
        await assign_lesson(db_session, world.learner, other)
        unassigned = await create_lesson(db_session, module, "Unassigned", sort_order=2)

        assignments = AssignmentRepository(db_session)
        everything = {lesson.id for lesson in [*world.lessons, world.lesson_a2, wanted, other]}

        assert await assignments.lesson_ids_for_user(world.learner.id) == everything
        assert await assignments.lesson_ids_for_user(world.learner.id, [wanted.id]) == {wanted.id}
        assert await assignments.lesson_ids_for_user(
            world.learner.id, [wanted.id, unassigned.id]
        ) == {wanted.id}
        assert await assignments.lesson_ids_for_user(world.learner.id, []) == set()

    async def test_next_lesson_does_not_skip_a_tied_sort_order(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """sort_order is not unique in legacy data. Two lessons sharing one must
        still form a sequence -- the strict `>` comparison skipped the tied
        sibling entirely. (The harness never commits, so C11's deferred unique
        constraint never fires here.)"""
        track = await create_track(db_session, "Tie Track", sort_order=31)
        module = await create_module(db_session, track, "Tie Module")
        first = await create_lesson(db_session, module, "First", sort_order=1)
        tied = await create_lesson(db_session, module, "Tied", sort_order=1)
        await assign_lesson(db_session, world.learner, first)
        await assign_lesson(db_session, world.learner, tied)
        earlier, later = sorted([first, tied], key=lambda lesson: (lesson.sort_order, lesson.id))

        response = await client.get(
            f"/api/lessons/{earlier.id}", headers=auth_headers(world.learner, test_settings)
        )

        assert response.status_code == 200
        assert response.json()["next_lesson_id"] == str(later.id)

    async def test_lesson_endpoints_read_assignments_scoped_not_unbounded(
        self, client: AsyncClient, world: World, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """Every user_lessons read on the three learner lesson paths carries an
        IN (...) candidate filter instead of pulling the caller's whole set."""
        seen: list[str] = []

        def _record(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
            seen.append(" ".join(statement.split()))

        headers = auth_headers(world.learner, test_settings)
        bind = db_session.get_bind()
        assert isinstance(bind, Connection)
        event.listen(bind, "before_cursor_execute", _record)
        try:
            responses = [
                await client.get(f"/api/modules/{world.module_a1.id}/lessons", headers=headers),
                await client.get(f"/api/lessons/{world.lessons[2].id}", headers=headers),
                await client.put(
                    f"/api/lessons/{world.lessons[1].id}/progress",
                    json={"answers": {}},
                    headers=headers,
                ),
            ]
        finally:
            event.remove(bind, "before_cursor_execute", _record)

        assert [r.status_code for r in responses] == [200, 200, 204]
        reads = [s for s in seen if s.startswith("SELECT user_lessons.lesson_id")]
        assert reads, "expected user_lessons reads"
        unbounded = [s for s in reads if "user_lessons.lesson_id IN" not in s]
        assert not unbounded, f"unscoped user_lessons reads: {unbounded}"
