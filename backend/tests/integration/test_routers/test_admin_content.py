"""Admin content management: track/module/lesson creation with server-side
sort_order arithmetic, module-insert shifting (DB6), batch reorder (B5)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest_asyncio

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_track,
    create_user,
    unlock_component,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


@pytest_asyncio.fixture
async def admin_headers(db_session: AsyncSession, test_settings: Settings) -> dict[str, str]:
    admin = await create_user(db_session, email="content-admin@example.com", role="admin")
    return auth_headers(admin, test_settings)


@pytest_asyncio.fixture
async def learning_project_id(db_session: AsyncSession) -> uuid.UUID:
    """A project with `learning` unlocked, for the viewer users below that hit
    the component-lock-gated learning endpoints (graph/modules/lessons)."""
    company = await create_company(db_session, "Content Viewer Co")
    project = await create_project(db_session, company, "Content Viewer Project")
    await unlock_component(db_session, project, "learning")
    return project.id


class TestTrackReads:
    async def test_tracks_visible_to_plain_users(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        track = await create_track(db_session, "Readable", color="#abc")
        user = await create_user(db_session, email="track-reader@example.com")
        response = await client.get("/api/tracks", headers=auth_headers(user, test_settings))
        assert response.status_code == 200
        entry = next(t for t in response.json() if t["id"] == str(track.id))
        assert entry == {
            "id": str(track.id),
            "name": "Readable",
            "sort_order": 0,
            "track_type": "general",
            "color": "#abc",
            "required_level": "explore",
            "is_introduction": False,
        }

    async def test_track_modules_ordered(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        track = await create_track(db_session, "Ordered")
        await create_module(db_session, track, "Second", sort_order=1)
        await create_module(db_session, track, "First", sort_order=0)
        user = await create_user(db_session, email="module-reader@example.com")
        response = await client.get(
            f"/api/tracks/{track.id}/modules", headers=auth_headers(user, test_settings)
        )
        assert [m["title"] for m in response.json()] == ["First", "Second"]

    async def test_unknown_track_is_404(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="lost-reader@example.com")
        response = await client.get(
            f"/api/tracks/{uuid.uuid4()}/modules", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 404


class TestCreateTrack:
    async def test_sort_order_is_max_plus_one(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        await create_track(db_session, "Existing", sort_order=4)
        response = await client.post(
            "/api/admin/tracks",
            json={"name": "Appended", "track_type": "tool", "color": "#fff"},
            headers=admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["sort_order"] == 5

    async def test_invalid_track_type_is_422(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.post(
            "/api/admin/tracks",
            json={"name": "Bad", "track_type": "banana"},
            headers=admin_headers,
        )
        assert response.status_code == 422


class TestCreateModule:
    async def test_append_without_predecessor(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        track = await create_track(db_session, "Append Track")
        await create_module(db_session, track, "M0", sort_order=0)
        response = await client.post(
            "/api/admin/modules",
            json={"track_id": str(track.id), "title": "M1"},
            headers=admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["sort_order"] == 1

    async def test_insert_after_shifts_successors(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict[str, str],
        test_settings: Settings,
    ) -> None:
        """The DB6 fix: inserting between modules renumbers successors instead
        of creating duplicate sort_orders."""
        track = await create_track(db_session, "Shift Track")
        first = await create_module(db_session, track, "First", sort_order=0)
        await create_module(db_session, track, "Third", sort_order=1)

        response = await client.post(
            "/api/admin/modules",
            json={"track_id": str(track.id), "title": "Second", "after_module_id": str(first.id)},
            headers=admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["sort_order"] == 1

        user = await create_user(db_session, email="shift-viewer@example.com")
        modules = (
            await client.get(
                f"/api/tracks/{track.id}/modules", headers=auth_headers(user, test_settings)
            )
        ).json()
        assert [(m["title"], m["sort_order"]) for m in modules] == [
            ("First", 0),
            ("Second", 1),
            ("Third", 2),
        ]

    async def test_prerequisites_inserted_atomically(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict[str, str],
        test_settings: Settings,
        learning_project_id: uuid.UUID,
    ) -> None:
        track = await create_track(db_session, "Prereq Track")
        base = await create_module(db_session, track, "Base", sort_order=0)
        response = await client.post(
            "/api/admin/modules",
            json={
                "track_id": str(track.id),
                "title": "Dependent",
                "prerequisite_ids": [str(base.id), str(base.id)],  # duplicates collapse
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        module_id = response.json()["id"]

        user = await create_user(
            db_session, email="prereq-viewer@example.com", project_id=learning_project_id
        )
        graph = (
            await client.get("/api/learning/graph", headers=auth_headers(user, test_settings))
        ).json()
        edges = [p for p in graph["prerequisites"] if p["module_id"] == module_id]
        assert edges == [{"module_id": module_id, "prerequisite_module_id": str(base.id)}]

    async def test_after_module_from_other_track_is_400(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        track = await create_track(db_session, "Main Track")
        other_track = await create_track(db_session, "Other Track", sort_order=1)
        foreign = await create_module(db_session, other_track, "Foreign")
        response = await client.post(
            "/api/admin/modules",
            json={
                "track_id": str(track.id),
                "title": "Misplaced",
                "after_module_id": str(foreign.id),
            },
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "bad_request"

    async def test_unknown_track_or_prerequisite_is_404(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        track = await create_track(db_session, "Known Track")
        assert (
            await client.post(
                "/api/admin/modules",
                json={"track_id": str(uuid.uuid4()), "title": "Orphan"},
                headers=admin_headers,
            )
        ).status_code == 404
        assert (
            await client.post(
                "/api/admin/modules",
                json={
                    "track_id": str(track.id),
                    "title": "Ghost prereq",
                    "prerequisite_ids": [str(uuid.uuid4())],
                },
                headers=admin_headers,
            )
        ).status_code == 404


class TestDeleteModule:
    async def test_delete_module_cascades_children(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict[str, str],
        test_settings: Settings,
    ) -> None:
        from sqlalchemy import func, select

        from src.db.models import Lesson, ModulePrerequisite, UserLesson, UserModule
        from tests.fixtures.factories import assign_lesson, assign_module, create_prerequisite

        track = await create_track(db_session, "Doomed Track")
        base = await create_module(db_session, track, "Base", sort_order=0)
        doomed = await create_module(db_session, track, "Doomed", sort_order=1)
        await create_prerequisite(db_session, doomed, base)
        lesson = await create_lesson(db_session, doomed, "Doomed Lesson")
        user = await create_user(db_session, email="module-loser@example.com")
        await assign_module(db_session, user, doomed)
        await assign_lesson(db_session, user, lesson)

        response = await client.delete(f"/api/admin/modules/{doomed.id}", headers=admin_headers)
        assert response.status_code == 204

        viewer = await create_user(db_session, email="module-check@example.com")
        remaining_modules = (
            await client.get(
                f"/api/tracks/{track.id}/modules", headers=auth_headers(viewer, test_settings)
            )
        ).json()
        assert [m["title"] for m in remaining_modules] == ["Base"]

        for model, column in (
            (Lesson, Lesson.module_id),
            (ModulePrerequisite, ModulePrerequisite.module_id),
            (UserModule, UserModule.module_id),
            (UserLesson, UserLesson.lesson_id),
        ):
            remaining = (
                await db_session.execute(
                    select(func.count())
                    .select_from(model)
                    .where(column == (doomed.id if model is not UserLesson else lesson.id))
                )
            ).scalar_one()
            assert remaining == 0, f"{model.__name__} row survived module delete"

    async def test_delete_unknown_module_is_404(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.delete(f"/api/admin/modules/{uuid.uuid4()}", headers=admin_headers)
        assert response.status_code == 404


class TestLessons:
    async def test_create_lesson_appends(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        track = await create_track(db_session, "Lesson Track")
        module = await create_module(db_session, track, "Lesson Module")
        await create_lesson(db_session, module, "Existing", sort_order=2)
        response = await client.post(
            "/api/admin/lessons",
            json={"module_id": str(module.id), "title": "Appended"},
            headers=admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["sort_order"] == 3

    async def test_create_lesson_unknown_module_is_404(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.post(
            "/api/admin/lessons",
            json={"module_id": str(uuid.uuid4()), "title": "Orphan"},
            headers=admin_headers,
        )
        assert response.status_code == 404

    async def test_patch_title_and_content_blocks(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        track = await create_track(db_session, "Patch Track")
        module = await create_module(db_session, track, "Patch Module")
        lesson = await create_lesson(db_session, module, "Draft title")
        blocks = [{"type": "text", "content": "Hello"}, {"type": "quiz", "question": "?"}]
        response = await client.patch(
            f"/api/admin/lessons/{lesson.id}",
            json={"title": "Final title", "content_blocks": blocks},
            headers=admin_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Final title"
        assert body["content_blocks"] == blocks

        # Partial patch keeps the other field.
        response = await client.patch(
            f"/api/admin/lessons/{lesson.id}",
            json={"title": "Renamed only"},
            headers=admin_headers,
        )
        assert response.json()["content_blocks"] == blocks

    async def test_patch_unknown_lesson_is_404(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.patch(
            f"/api/admin/lessons/{uuid.uuid4()}", json={"title": "X"}, headers=admin_headers
        )
        assert response.status_code == 404

    async def test_delete_lesson_cascades_progress(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict[str, str],
        test_settings: Settings,
        learning_project_id: uuid.UUID,
    ) -> None:
        from sqlalchemy import func, select

        from src.db.models import LessonProgress
        from tests.fixtures.factories import complete_lesson

        track = await create_track(db_session, "Delete Track")
        module = await create_module(db_session, track, "Delete Module")
        lesson = await create_lesson(db_session, module, "Doomed")
        user = await create_user(
            db_session, email="lesson-loser@example.com", project_id=learning_project_id
        )
        await complete_lesson(db_session, user, lesson)

        response = await client.delete(f"/api/admin/lessons/{lesson.id}", headers=admin_headers)
        assert response.status_code == 204
        assert (
            await client.get(f"/api/lessons/{lesson.id}", headers=auth_headers(user, test_settings))
        ).status_code == 404
        orphans = (
            await db_session.execute(
                select(func.count())
                .select_from(LessonProgress)
                .where(LessonProgress.lesson_id == lesson.id)
            )
        ).scalar_one()
        assert orphans == 0


class TestReorderLessons:
    async def test_batch_reorder_applies_positions(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict[str, str],
        test_settings: Settings,
        learning_project_id: uuid.UUID,
    ) -> None:
        track = await create_track(db_session, "Reorder Track")
        module = await create_module(db_session, track, "Reorder Module")
        lessons = [await create_lesson(db_session, module, f"L{i}", sort_order=i) for i in range(3)]
        reversed_ids = [str(lesson.id) for lesson in reversed(lessons)]
        response = await client.put(
            f"/api/admin/modules/{module.id}/lessons/order",
            json={"lesson_ids": reversed_ids},
            headers=admin_headers,
        )
        assert response.status_code == 204

        user = await create_user(
            db_session, email="reorder-viewer@example.com", project_id=learning_project_id
        )
        listed = (
            await client.get(
                f"/api/modules/{module.id}/lessons", headers=auth_headers(user, test_settings)
            )
        ).json()["lessons"]
        assert [lesson["title"] for lesson in listed] == ["L2", "L1", "L0"]
        assert [lesson["sort_order"] for lesson in listed] == [0, 1, 2]

    async def test_mismatched_set_is_400(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        track = await create_track(db_session, "Mismatch Track")
        module = await create_module(db_session, track, "Mismatch Module")
        lessons = [await create_lesson(db_session, module, f"L{i}", sort_order=i) for i in range(2)]
        url = f"/api/admin/modules/{module.id}/lessons/order"

        # Missing a lesson.
        assert (
            await client.put(url, json={"lesson_ids": [str(lessons[0].id)]}, headers=admin_headers)
        ).status_code == 400
        # Duplicated id padding out the count.
        assert (
            await client.put(
                url,
                json={"lesson_ids": [str(lessons[0].id), str(lessons[0].id)]},
                headers=admin_headers,
            )
        ).status_code == 400
        # Foreign lesson id.
        assert (
            await client.put(
                url,
                json={"lesson_ids": [str(lessons[0].id), str(uuid.uuid4())]},
                headers=admin_headers,
            )
        ).status_code == 400

    async def test_reorder_unknown_module_is_404(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.put(
            f"/api/admin/modules/{uuid.uuid4()}/lessons/order",
            json={"lesson_ids": []},
            headers=admin_headers,
        )
        assert response.status_code == 404


class TestLessonUpdateLinkSchemes:
    """PATCH deliberately skips the full structural validator (most live lessons
    predate it), but the url-scheme allowlist is narrow enough to apply here --
    and it is the only thing standing between pasted MDX and a javascript: link
    going live."""

    async def test_disallowed_scheme_is_rejected(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict[str, str],
    ) -> None:
        track = await create_track(db_session, "Scheme Track")
        module = await create_module(db_session, track, "Scheme Module")
        lesson = await create_lesson(db_session, module, "Scheme Lesson")

        response = await client.patch(
            f"/api/admin/lessons/{lesson.id}",
            json={
                "content_blocks": [
                    {"id": "b1", "type": "paragraph", "text": "[click](javascript:alert(1))"}
                ]
            },
            headers=admin_headers,
        )

        assert response.status_code == 400
        assert "javascript" in response.json()["error"]["message"]
        await db_session.refresh(lesson)
        assert lesson.content_blocks == []

    async def test_ordinary_lesson_content_still_saves(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict[str, str],
    ) -> None:
        """A structurally imperfect but harmless payload (the common case for
        the real corpus) must still save -- this task adds the scheme check
        only, not the structural validator."""
        track = await create_track(db_session, "Scheme Ok Track")
        module = await create_module(db_session, track, "Scheme Ok Module")
        lesson = await create_lesson(db_session, module, "Scheme Ok Lesson")

        blocks = [
            {"id": "b1", "type": "paragraph", "text": "See [the docs](https://example.com)."},
            {"type": "markdown", "body": "no id, unknown type -- still fine here"},
        ]
        response = await client.patch(
            f"/api/admin/lessons/{lesson.id}",
            json={"content_blocks": blocks},
            headers=admin_headers,
        )

        assert response.status_code == 200
        await db_session.refresh(lesson)
        assert lesson.content_blocks == blocks
