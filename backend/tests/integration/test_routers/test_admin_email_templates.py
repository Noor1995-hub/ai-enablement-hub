"""Per-project email template CRUD + preview endpoints (admin-only). Default
conftest client — these routes touch only the DB and settings, no ACS."""

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
    from src.db.models import Project


@pytest_asyncio.fixture
async def project(db_session: AsyncSession) -> Project:
    company = await create_company(db_session, "Templates Co")
    return await create_project(db_session, company, "Templates Project")


@pytest_asyncio.fixture
async def headers(db_session: AsyncSession, test_settings: Settings) -> dict[str, str]:
    admin = await create_user(db_session, email="tpl-admin@example.com", role="admin")
    return auth_headers(admin, test_settings)


def _base(project: Project) -> str:
    return f"/api/admin/projects/{project.id}/email-templates"


class TestGetDefaults:
    async def test_fresh_project_returns_both_defaults(
        self, client: AsyncClient, project: Project, headers: dict[str, str]
    ) -> None:
        response = await client.get(_base(project), headers=headers)
        assert response.status_code == 200
        by_purpose = {t["purpose"]: t for t in response.json()["templates"]}
        assert set(by_purpose) == {"invite", "reset"}
        assert all(t["is_custom"] is False for t in by_purpose.values())
        assert "{{invite_link}}" in by_purpose["invite"]["body_markdown"]
        assert "{{reset_link}}" in by_purpose["reset"]["body_markdown"]

    async def test_unknown_project_is_404(
        self, client: AsyncClient, headers: dict[str, str]
    ) -> None:
        response = await client.get(
            f"/api/admin/projects/{uuid.uuid4()}/email-templates", headers=headers
        )
        assert response.status_code == 404


class TestUpsertAndRevert:
    async def test_put_then_get_reflects_the_override(
        self, client: AsyncClient, project: Project, headers: dict[str, str]
    ) -> None:
        put = await client.put(
            f"{_base(project)}/invite",
            json={"subject": "Join {{project_name}}", "body_markdown": "Hi\n\n{{invite_link}}"},
            headers=headers,
        )
        assert put.status_code == 204

        templates = (await client.get(_base(project), headers=headers)).json()["templates"]
        invite = next(t for t in templates if t["purpose"] == "invite")
        assert invite["is_custom"] is True
        assert invite["subject"] == "Join {{project_name}}"
        # The other purpose is untouched (still the default).
        reset = next(t for t in templates if t["purpose"] == "reset")
        assert reset["is_custom"] is False

    async def test_delete_reverts_to_default(
        self, client: AsyncClient, project: Project, headers: dict[str, str]
    ) -> None:
        await client.put(
            f"{_base(project)}/invite",
            json={"subject": "Custom", "body_markdown": "{{invite_link}}"},
            headers=headers,
        )
        delete = await client.delete(f"{_base(project)}/invite", headers=headers)
        assert delete.status_code == 204

        templates = (await client.get(_base(project), headers=headers)).json()["templates"]
        invite = next(t for t in templates if t["purpose"] == "invite")
        assert invite["is_custom"] is False
        assert invite["subject"] == "You're invited to the delaware AI Enablement Hub"

    async def test_put_missing_link_token_is_400(
        self, client: AsyncClient, project: Project, headers: dict[str, str]
    ) -> None:
        response = await client.put(
            f"{_base(project)}/invite",
            json={"subject": "Hi", "body_markdown": "No link here, sorry."},
            headers=headers,
        )
        assert response.status_code == 400

    async def test_put_unknown_token_is_400(
        self, client: AsyncClient, project: Project, headers: dict[str, str]
    ) -> None:
        response = await client.put(
            f"{_base(project)}/invite",
            json={"subject": "Hi {{bogus}}", "body_markdown": "{{invite_link}}"},
            headers=headers,
        )
        assert response.status_code == 400

    async def test_bad_purpose_is_422(
        self, client: AsyncClient, project: Project, headers: dict[str, str]
    ) -> None:
        response = await client.put(
            f"{_base(project)}/nonsense",
            json={"subject": "Hi", "body_markdown": "{{invite_link}}"},
            headers=headers,
        )
        assert response.status_code == 422


class TestPreview:
    async def test_preview_renders_html_with_sample_values(
        self, client: AsyncClient, project: Project, headers: dict[str, str]
    ) -> None:
        response = await client.post(
            f"{_base(project)}/invite/preview",
            json={
                "subject": "Welcome {{first_name}} to {{project_name}}",
                "body_markdown": "Hi **{{first_name}}**\n\n[Set password]({{invite_link}})",
            },
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subject"] == "Welcome Alex to Templates Project"
        assert "<strong>Alex</strong>" in data["html"]
        assert 'href="' in data["html"]
        assert "example-invite-token" in data["html"]
        assert "example-invite-token" in data["plain_text"]

    async def test_preview_unknown_project_is_404(
        self, client: AsyncClient, headers: dict[str, str]
    ) -> None:
        response = await client.post(
            f"/api/admin/projects/{uuid.uuid4()}/email-templates/invite/preview",
            json={"subject": "s", "body_markdown": "{{invite_link}}"},
            headers=headers,
        )
        assert response.status_code == 404
