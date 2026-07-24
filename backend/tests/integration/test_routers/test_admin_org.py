"""Admin org endpoints: companies, projects, component settings."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest_asyncio

from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_company, create_project, create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings


@pytest_asyncio.fixture
async def admin_headers(db_session: AsyncSession, test_settings: Settings) -> dict[str, str]:
    admin = await create_user(db_session, email="org-admin@example.com", role="admin")
    return auth_headers(admin, test_settings)


class TestCompanies:
    async def test_list_nests_projects_per_company(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        acme = await create_company(db_session, "Acme")
        await create_company(db_session, "Beta")
        project = await create_project(db_session, acme, "Acme Rollout")

        response = await client.get("/api/admin/companies", headers=admin_headers)
        assert response.status_code == 200
        companies = {c["name"]: c for c in response.json()["companies"]}
        assert [p["id"] for p in companies["Acme"]["projects"]] == [str(project.id)]
        assert companies["Beta"]["projects"] == []
        assert companies["Acme"]["id"] == str(acme.id)

    async def test_create_company(self, client: AsyncClient, admin_headers: dict[str, str]) -> None:
        response = await client.post(
            "/api/admin/companies", json={"name": "  New Co  "}, headers=admin_headers
        )
        assert response.status_code == 201
        assert response.json()["name"] == "New Co"

    async def test_duplicate_name_is_409_case_insensitive(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        await create_company(db_session, "Duplicate Co")
        response = await client.post(
            "/api/admin/companies", json={"name": "dUpLiCaTe cO"}, headers=admin_headers
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflict"

    async def test_blank_name_is_422(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.post(
            "/api/admin/companies", json={"name": "   "}, headers=admin_headers
        )
        assert response.status_code == 422


class TestProjects:
    async def test_create_project_seeds_default_component_settings(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        company = await create_company(db_session, "Proj Co")
        response = await client.post(
            "/api/admin/projects",
            json={"name": "Fresh Project", "company_id": str(company.id)},
            headers=admin_headers,
        )
        assert response.status_code == 201
        project_id = response.json()["id"]
        assert response.json()["company_id"] == str(company.id)

        from sqlalchemy import select

        from src.db.models import ProjectComponentSetting

        rows = (
            (
                await db_session.execute(
                    select(ProjectComponentSetting).where(
                        ProjectComponentSetting.project_id == uuid.UUID(project_id)
                    )
                )
            )
            .scalars()
            .all()
        )
        settings_by_component = {row.component: (row.hidden, row.locked) for row in rows}
        assert settings_by_component == {
            "assessment": (False, False),
            "learning": (False, True),
            "interview": (False, True),
        }

    async def test_unknown_company_is_404(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.post(
            "/api/admin/projects",
            json={"name": "Orphan", "company_id": str(uuid.uuid4())},
            headers=admin_headers,
        )
        assert response.status_code == 404


class TestComponents:
    async def test_defaults_fallback_when_no_rows(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        company = await create_company(db_session, "Comp Co")
        project = await create_project(db_session, company)  # bare, no settings rows
        response = await client.get(
            f"/api/admin/projects/{project.id}/components", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["components"] == {
            "assessment": {"hidden": False, "locked": False},
            "learning": {"hidden": False, "locked": True},
            "interview": {"hidden": False, "locked": True},
        }

    async def test_unknown_project_is_404(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.get(
            f"/api/admin/projects/{uuid.uuid4()}/components", headers=admin_headers
        )
        assert response.status_code == 404

    async def test_partial_put_merges_with_defaults_then_stored_state(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        company = await create_company(db_session, "Merge Co")
        project = await create_project(db_session, company)
        base = f"/api/admin/projects/{project.id}/components"

        # Only hidden supplied: locked falls back to the default (True for learning).
        response = await client.put(
            f"{base}/learning", json={"hidden": True}, headers=admin_headers
        )
        assert response.status_code == 204
        components = (await client.get(base, headers=admin_headers)).json()["components"]
        assert components["learning"] == {"hidden": True, "locked": True}

        # Only locked supplied: the previously stored hidden=True is preserved.
        await client.put(f"{base}/learning", json={"locked": False}, headers=admin_headers)
        components = (await client.get(base, headers=admin_headers)).json()["components"]
        assert components["learning"] == {"hidden": True, "locked": False}

    async def test_invalid_component_name_is_422(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict[str, str]
    ) -> None:
        company = await create_company(db_session, "Bad Comp Co")
        project = await create_project(db_session, company)
        response = await client.put(
            f"/api/admin/projects/{project.id}/components/banana",
            json={"hidden": True},
            headers=admin_headers,
        )
        assert response.status_code == 422


class TestAiSettings:
    async def test_get_defaults_all_false(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="ai-settings-admin@example.com", role="admin")
        company = await create_company(db_session, "AI Settings Co")
        project = await create_project(db_session, company, "AI Settings Project")

        response = await client.get(
            f"/api/admin/projects/{project.id}/ai", headers=auth_headers(admin, test_settings)
        )

        assert response.status_code == 200
        settings = response.json()["settings"]
        assert all(v["enabled"] is False for v in settings.values())
        assert set(settings) == {"chatbot", "assessment", "lesson", "interview"}

    async def test_put_enables_one_surface(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="ai-settings-admin-2@example.com", role="admin")
        company = await create_company(db_session, "AI Settings Co 2")
        project = await create_project(db_session, company, "AI Settings Project 2")

        put_response = await client.put(
            f"/api/admin/projects/{project.id}/ai/chatbot",
            json={"enabled": True},
            headers=auth_headers(admin, test_settings),
        )
        assert put_response.status_code == 204

        get_response = await client.get(
            f"/api/admin/projects/{project.id}/ai", headers=auth_headers(admin, test_settings)
        )
        assert get_response.json()["settings"]["chatbot"]["enabled"] is True
        assert get_response.json()["settings"]["lesson"]["enabled"] is False

    async def test_non_admin_is_403(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="ai-settings-user@example.com")
        company = await create_company(db_session, "AI Settings Co 3")
        project = await create_project(db_session, company, "AI Settings Project 3")

        response = await client.get(
            f"/api/admin/projects/{project.id}/ai", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403
