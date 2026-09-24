"""Admin System-Prompts read-only API (admin-only). Default conftest client —
these routes touch only the filesystem, no DB/ACS/Blob/Anthropic."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest_asyncio

from src.services import prompts as P
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import User


@pytest_asyncio.fixture(autouse=True)
async def _clear_prompt_cache():
    """The prompt cache (`src.services.prompts`) is a process-global dict —
    clear it around every test so no state leaks between tests."""
    P.clear_cache()
    yield
    P.clear_cache()


@pytest_asyncio.fixture
async def admin(db_session: AsyncSession) -> User:
    return await create_user(db_session, email="prompt-admin@example.com", role="admin")


@pytest_asyncio.fixture
async def admin_headers(admin: User, test_settings: Settings) -> dict[str, str]:
    return auth_headers(admin, test_settings)


class TestList:
    async def test_list_as_admin_contains_all_nine_kinds(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/admin/prompts", headers=admin_headers)
        assert response.status_code == 200
        prompts = response.json()["prompts"]
        assert len(prompts) == 9
        assert {p["path"] for p in prompts} == {f"backend/prompts/{p['kind']}.md" for p in prompts}
        assert "source" not in prompts[0]

    async def test_non_admin_is_403(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="prompt-user@example.com", role="user")
        response = await client.get("/api/admin/prompts", headers=auth_headers(user, test_settings))
        assert response.status_code == 403


class TestDetail:
    async def test_detail_returns_file_content(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/admin/prompts/interview", headers=admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["content"].startswith("You are the AI Opportunity Interviewer")
        assert body["path"] == "backend/prompts/interview.md"

    async def test_unknown_kind_is_404(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/admin/prompts/does_not_exist", headers=admin_headers)
        assert response.status_code == 404


class TestNoWritePath:
    async def test_put_is_405(self, client: AsyncClient, admin_headers: dict[str, str]) -> None:
        response = await client.put(
            "/api/admin/prompts/interview", json={"content": "x"}, headers=admin_headers
        )
        assert response.status_code == 405

    async def test_delete_is_405(self, client: AsyncClient, admin_headers: dict[str, str]) -> None:
        response = await client.delete("/api/admin/prompts/interview", headers=admin_headers)
        assert response.status_code == 405
