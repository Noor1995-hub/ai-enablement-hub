"""Interview router gates. Deliberately LLM-free: test_settings.llm is None, so
get_interview_service resolves to None and a request that passes both gates
reaches the body and 404s "Interview is not configured". That 404 is the proof
the gates passed -- router-level dependencies run before the handler body, so a
gate rejection surfaces as 403 first. This is also the first HTTP-level coverage
of require_interview_surface (review 4.5)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest_asyncio

from src.repositories.org_repository import OrgRepository
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    create_company,
    create_project,
    create_survey,
    create_user,
    unlock_component,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import Project


@pytest_asyncio.fixture
async def project(db_session: AsyncSession) -> Project:
    company = await create_company(db_session, "Interview Gate Co")
    return await create_project(db_session, company, "Interview Gate Project")


async def _enable_interview_ai(db_session: AsyncSession, project_id: uuid.UUID) -> None:
    await OrgRepository(db_session).upsert_ai_setting(project_id, "interview", enabled=True)


class TestInterviewComponentGate:
    async def test_403_when_the_interview_component_is_locked_by_default(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        """A fresh project defaults `interview` to locked=True. Enabling the AI
        surface must not be enough on its own."""
        await _enable_interview_ai(db_session, project.id)
        user = await create_user(
            db_session, email="interview-locked@example.com", project_id=project.id
        )

        response = await client.get("/api/interview/me", headers=auth_headers(user, test_settings))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        assert "interview component" in response.json()["error"]["message"]

    async def test_403_when_the_component_is_hidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await unlock_component(db_session, project, "interview", hidden=True)
        await _enable_interview_ai(db_session, project.id)
        user = await create_user(
            db_session, email="interview-hidden@example.com", project_id=project.id
        )

        response = await client.get("/api/interview/me", headers=auth_headers(user, test_settings))
        assert response.status_code == 403
        assert "interview component" in response.json()["error"]["message"]

    async def test_both_gates_open_reaches_the_handler(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        """404 "not configured" (llm=None in test settings) proves both the
        component gate and the AI-surface gate passed."""
        await unlock_component(db_session, project, "interview")
        await _enable_interview_ai(db_session, project.id)
        user = await create_user(
            db_session, email="interview-open@example.com", project_id=project.id
        )

        response = await client.get("/api/interview/me", headers=auth_headers(user, test_settings))
        assert response.status_code == 404
        assert "not configured" in response.json()["error"]["message"]

    async def test_403_when_the_ai_surface_is_disabled(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        """Component unlocked but the interview AI surface never enabled."""
        await unlock_component(db_session, project, "interview")
        user = await create_user(
            db_session, email="interview-surface-off@example.com", project_id=project.id
        )

        response = await client.get("/api/interview/me", headers=auth_headers(user, test_settings))
        assert response.status_code == 403

    async def test_admin_bypasses_a_locked_interview(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        """Spec 2026-10-01 decision 5: a power admin bypasses a `locked`
        component (interview is locked by default); `hidden` still applies —
        see test_component_lock.py::test_admin_bypasses_locked_but_not_hidden."""
        await _enable_interview_ai(db_session, project.id)
        admin = await create_user(
            db_session,
            email="interview-locked-admin@example.com",
            role="admin",
            project_id=project.id,
        )

        response = await client.get("/api/interview/me", headers=auth_headers(admin, test_settings))
        # Past both router gates: this client has no LLM configured, so the
        # handler itself answers 404 "not configured" rather than 403.
        assert response.status_code != 403

    async def test_anonymous_is_401(self, client: AsyncClient) -> None:
        assert (await client.get("/api/interview/me")).status_code == 401

    async def test_opener_and_playbook_are_gated_too(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        """The gate is router-level, so it covers every route on it."""
        await _enable_interview_ai(db_session, project.id)
        user = await create_user(
            db_session, email="interview-writes@example.com", project_id=project.id
        )
        headers = auth_headers(user, test_settings)

        assert (await client.post("/api/interview/opener", headers=headers)).status_code == 403
        assert (await client.post("/api/interview/playbook", headers=headers)).status_code == 403


class TestAdminInterviewIsNotComponentGated:
    async def test_admin_view_works_regardless_of_component_flags(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        """/api/admin/interviews/{user_id} must not depend on the admin's own
        project component flags -- 404 (llm unconfigured), never 403."""
        admin = await create_user(
            db_session, email="admin-interview-reader@example.com", role="admin"
        )
        learner = await create_user(
            db_session, email="admin-interview-subject@example.com", project_id=project.id
        )

        response = await client.get(
            f"/api/admin/interviews/{learner.id}",
            headers=auth_headers(admin, test_settings),
        )
        assert response.status_code == 404
        assert "not configured" in response.json()["error"]["message"]


class TestAssessmentGate:
    """Spec 2026-09-26 A.3.5: normal users need a COMPLETED assessment; admins are exempt.
    404 "not configured" (llm=None in test settings) proves every gate passed."""

    async def _open_project(self, db_session: AsyncSession, project: Project) -> None:
        await unlock_component(db_session, project, "interview")
        await _enable_interview_ai(db_session, project.id)

    async def test_no_assessment_is_403_on_opener_and_playbook(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await self._open_project(db_session, project)
        user = await create_user(db_session, email="gate-none@example.com", project_id=project.id)
        headers = auth_headers(user, test_settings)

        for path in ("/api/interview/opener", "/api/interview/playbook"):
            response = await client.post(path, headers=headers)
            assert response.status_code == 403
            assert "Complete your assessment" in response.json()["error"]["message"]

    async def test_a_draft_assessment_is_not_enough(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await self._open_project(db_session, project)
        user = await create_user(db_session, email="gate-draft@example.com", project_id=project.id)
        await create_survey(db_session, user, status="in_progress")

        response = await client.post(
            "/api/interview/opener", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403

    async def test_a_completed_assessment_passes(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await self._open_project(db_session, project)
        user = await create_user(db_session, email="gate-done@example.com", project_id=project.id)
        await create_survey(db_session, user, status="complete")

        response = await client.post(
            "/api/interview/opener", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 404
        assert "not configured" in response.json()["error"]["message"]

    async def test_the_opener_accepts_a_language_choice(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        """#83: the welcome screen posts the learner's pick. Past validation the route
        reaches the (unconfigured) service, so 404, not 422; an unknown language is 422."""
        await self._open_project(db_session, project)
        user = await create_user(db_session, email="gate-lang@example.com", project_id=project.id)
        await create_survey(db_session, user, status="complete")
        headers = auth_headers(user, test_settings)

        dutch = await client.post("/api/interview/opener", headers=headers, json={"language": "nl"})
        french = await client.post(
            "/api/interview/opener", headers=headers, json={"language": "fr"}
        )

        assert dutch.status_code == 404
        assert french.status_code == 422

    async def test_admin_without_assessment_passes(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await self._open_project(db_session, project)
        admin = await create_user(
            db_session, email="gate-admin@example.com", role="admin", project_id=project.id
        )

        response = await client.post(
            "/api/interview/opener", headers=auth_headers(admin, test_settings)
        )
        assert response.status_code == 404

    async def test_state_endpoint_is_not_gated(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        """A learner with an existing playbook but no assessment must still read it."""
        await self._open_project(db_session, project)
        user = await create_user(db_session, email="gate-me@example.com", project_id=project.id)

        response = await client.get("/api/interview/me", headers=auth_headers(user, test_settings))
        assert response.status_code == 404

    async def test_interview_chat_turn_is_gated(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        project: Project,
        test_settings: Settings,
    ) -> None:
        await self._open_project(db_session, project)
        user = await create_user(db_session, email="gate-chat@example.com", project_id=project.id)

        response = await client.post(
            "/api/chat/interview",
            json={"content": "hello"},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 403
        assert "Complete your assessment" in response.json()["error"]["message"]
