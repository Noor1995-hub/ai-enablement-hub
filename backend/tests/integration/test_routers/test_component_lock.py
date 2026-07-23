"""Component-lock hard gate: a project's assessment/learning hidden|locked
flags (project_component_settings) used to be a display-only hint for
JourneyHome — any authenticated user could still call the survey/learning
endpoints directly regardless of what the hub tile showed. This covers the
backend enforcement that closes that gap: `require_component_unlocked`."""

from __future__ import annotations

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
    from src.db.models import Lesson, Project


@pytest_asyncio.fixture
async def project(db_session: AsyncSession) -> Project:
    company = await create_company(db_session, "Lock Co")
    return await create_project(db_session, company, "Lock Project")


@pytest_asyncio.fixture
async def lesson(db_session: AsyncSession) -> Lesson:
    track = await create_track(db_session, "Lock Track")
    module = await create_module(db_session, track, "Lock Module")
    return await create_lesson(db_session, module, "Lock Lesson")


class TestLearningLockedByDefault:
    """A fresh project defaults learning to locked=True (core/constants.py) —
    that must now reject, not just display, until an admin unlocks it."""

    async def test_graph_403_when_learning_locked_by_default(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        user = await create_user(
            db_session, email="locked-learner@example.com", project_id=project.id
        )
        response = await client.get(
            "/api/learning/graph", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    async def test_module_lessons_403_when_learning_locked(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        lesson: Lesson,
        test_settings: Settings,
    ) -> None:
        user = await create_user(
            db_session, email="locked-module-viewer@example.com", project_id=project.id
        )
        response = await client.get(
            f"/api/modules/{lesson.module_id}/lessons", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403

    async def test_lesson_detail_403_when_learning_locked(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        lesson: Lesson,
        test_settings: Settings,
    ) -> None:
        user = await create_user(
            db_session, email="locked-lesson-viewer@example.com", project_id=project.id
        )
        response = await client.get(
            f"/api/lessons/{lesson.id}", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403

    async def test_progress_403_when_learning_locked(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        lesson: Lesson,
        test_settings: Settings,
    ) -> None:
        user = await create_user(
            db_session, email="locked-progress-user@example.com", project_id=project.id
        )
        response = await client.put(
            f"/api/lessons/{lesson.id}/progress",
            json={"answers": {}},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 403

    async def test_user_without_a_project_is_also_locked_out(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        """No project at all resolves to the same defaults (org_service.
        resolve_components) — this was the exact loophole: a project-less
        caller could still hit every learning endpoint directly."""
        user = await create_user(db_session, email="no-project-learner@example.com")
        response = await client.get(
            "/api/learning/graph", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403

    async def test_admin_is_not_exempt(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        """Per the user+ design doc: component locks are a project-level gate,
        not a learning-path requirement — neither admin nor user+ bypass it."""
        admin = await create_user(
            db_session, email="locked-admin@example.com", role="admin", project_id=project.id
        )
        response = await client.get(
            "/api/learning/graph", headers=auth_headers(admin, test_settings)
        )
        assert response.status_code == 403


class TestLearningUnlocked:
    async def test_graph_succeeds_once_unlocked(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await unlock_component(db_session, project, "learning")
        user = await create_user(
            db_session, email="unlocked-learner@example.com", project_id=project.id
        )
        response = await client.get(
            "/api/learning/graph", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 200

    async def test_hidden_also_rejects_even_if_not_locked(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await unlock_component(db_session, project, "learning", hidden=True)
        user = await create_user(
            db_session, email="hidden-learner@example.com", project_id=project.id
        )
        response = await client.get(
            "/api/learning/graph", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403


class TestAssessmentUnlockedByDefault:
    """assessment defaults to locked=False, so the gate must not regress the
    common case — only an explicit lock should 403."""

    async def test_survey_get_open_by_default(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        user = await create_user(
            db_session, email="default-open-survey@example.com", project_id=project.id
        )
        response = await client.get("/api/survey/me", headers=auth_headers(user, test_settings))
        assert response.status_code == 200

    async def test_survey_403_once_admin_locks_it(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await unlock_component(db_session, project, "assessment", locked=True)

        user = await create_user(
            db_session, email="locked-survey-user@example.com", project_id=project.id
        )
        response = await client.get("/api/survey/me", headers=auth_headers(user, test_settings))
        assert response.status_code == 403

    async def test_survey_put_and_complete_also_gated(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await unlock_component(db_session, project, "assessment", locked=True)

        user = await create_user(
            db_session, email="locked-survey-writer@example.com", project_id=project.id
        )
        headers = auth_headers(user, test_settings)
        assert (
            await client.put("/api/survey/me", json={"job_title": "Dev"}, headers=headers)
        ).status_code == 403
        assert (await client.post("/api/survey/complete", headers=headers)).status_code == 403
