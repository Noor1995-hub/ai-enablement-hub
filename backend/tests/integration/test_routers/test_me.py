from __future__ import annotations

from typing import TYPE_CHECKING

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    assign_lesson,
    complete_lesson,
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_survey,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


class TestProfile:
    async def test_profile_shape(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        company = await create_company(db_session)
        project = await create_project(db_session, company)
        user = await create_user(
            db_session,
            email="profile@example.com",
            password="hunter2hunter2",
            first_name="Pro",
            last_name="File",
            company_id=company.id,
            project_id=project.id,
        )
        response = await client.get("/api/me", headers=auth_headers(user, test_settings))
        assert response.status_code == 200
        assert response.json() == {
            "id": str(user.id),
            "email": "profile@example.com",
            "first_name": "Pro",
            "last_name": "File",
            "role": "user",
            "company_id": str(company.id),
            "project_id": str(project.id),
            "password_set": True,
            "external_login": False,
        }


class TestJourney:
    async def test_defaults_without_project(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="no-project@example.com")
        response = await client.get("/api/me/journey", headers=auth_headers(user, test_settings))
        assert response.status_code == 200
        assert response.json() == {
            "components": {
                "assessment": {"hidden": False, "locked": False},
                "learning": {"hidden": False, "locked": True},
                "interview": {"hidden": False, "locked": True},
            },
            "survey_status": "not_started",
            "learning_status": "not_started",
        }

    async def test_defaults_for_project_without_settings_rows(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        company = await create_company(db_session)
        project = await create_project(db_session, company)
        user = await create_user(
            db_session,
            email="bare-project@example.com",
            company_id=company.id,
            project_id=project.id,
        )
        response = await client.get("/api/me/journey", headers=auth_headers(user, test_settings))
        assert response.json()["components"]["learning"] == {"hidden": False, "locked": True}

    async def test_project_settings_override_defaults(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_settings: Settings,
    ) -> None:
        from src.db.models import ProjectComponentSetting

        company = await create_company(db_session)
        project = await create_project(db_session, company)
        db_session.add(
            ProjectComponentSetting(
                project_id=project.id, component="learning", hidden=True, locked=False
            )
        )
        await db_session.commit()
        user = await create_user(
            db_session,
            email="tuned-project@example.com",
            company_id=company.id,
            project_id=project.id,
        )
        response = await client.get("/api/me/journey", headers=auth_headers(user, test_settings))
        components = response.json()["components"]
        assert components["learning"] == {"hidden": True, "locked": False}
        # Untouched components still fall back to defaults.
        assert components["assessment"] == {"hidden": False, "locked": False}

    async def test_survey_status_progression(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="journey-survey@example.com")
        headers = auth_headers(user, test_settings)

        assert (await client.get("/api/me/journey", headers=headers)).json()[
            "survey_status"
        ] == "not_started"

        await create_survey(db_session, user, status="in_progress")
        assert (await client.get("/api/me/journey", headers=headers)).json()[
            "survey_status"
        ] == "in_progress"

        response = await client.post("/api/survey/complete", headers=headers)
        assert response.status_code == 200
        assert (await client.get("/api/me/journey", headers=headers)).json()[
            "survey_status"
        ] == "complete"

    async def test_learning_status_progression(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="journey-learning@example.com")
        headers = auth_headers(user, test_settings)

        track = await create_track(db_session)
        module = await create_module(db_session, track)
        lesson_a = await create_lesson(db_session, module, "A", sort_order=0)
        lesson_b = await create_lesson(db_session, module, "B", sort_order=1)

        # No assigned lessons yet → not started.
        assert (await client.get("/api/me/journey", headers=headers)).json()[
            "learning_status"
        ] == "not_started"

        # Assigned but nothing completed → still not started.
        await assign_lesson(db_session, user, lesson_a)
        await assign_lesson(db_session, user, lesson_b)
        assert (await client.get("/api/me/journey", headers=headers)).json()[
            "learning_status"
        ] == "not_started"

        # One of two assigned lessons completed → in progress.
        await complete_lesson(db_session, user, lesson_a)
        assert (await client.get("/api/me/journey", headers=headers)).json()[
            "learning_status"
        ] == "in_progress"

        # Every assigned lesson completed → complete.
        await complete_lesson(db_session, user, lesson_b)
        assert (await client.get("/api/me/journey", headers=headers)).json()[
            "learning_status"
        ] == "complete"
