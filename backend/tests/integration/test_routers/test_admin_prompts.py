"""Admin System-Prompts editor CRUD (admin-only). Default conftest client —
these routes touch only the DB, no ACS/Blob/Anthropic."""

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


_KNOWN_KINDS = {
    "interview",
    "interview_playbook",
    "chatbot",
    "assessment",
    "lesson",
    "content_improvement",
    "content_improvement_critique",
    "house_style",
    "feedback_triage",
}


@pytest_asyncio.fixture(autouse=True)
async def _clear_prompt_cache():
    """The prompt cache (`src.services.prompts`) is a process-global dict, not
    scoped to the per-test DB transaction — clear it around every test so a
    save/reset in one test can't leak into another."""
    P.clear_cache()
    yield
    P.clear_cache()


@pytest_asyncio.fixture
async def admin(db_session: AsyncSession) -> User:
    return await create_user(db_session, email="prompt-admin@example.com", role="admin")


@pytest_asyncio.fixture
async def admin_headers(admin: User, test_settings: Settings) -> dict[str, str]:
    return auth_headers(admin, test_settings)


class TestListPrompts:
    async def test_list_as_admin_contains_all_nine_kinds(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/admin/prompts", headers=admin_headers)
        assert response.status_code == 200
        kinds = {p["kind"] for p in response.json()["prompts"]}
        assert kinds == _KNOWN_KINDS

    async def test_interview_source_flips_to_db_after_a_put(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        before = await client.get("/api/admin/prompts", headers=admin_headers)
        interview_before = next(p for p in before.json()["prompts"] if p["kind"] == "interview")
        assert interview_before["source"] == "file"

        put = await client.put(
            "/api/admin/prompts/interview", json={"content": "NEW"}, headers=admin_headers
        )
        assert put.status_code == 200

        after = await client.get("/api/admin/prompts", headers=admin_headers)
        interview_after = next(p for p in after.json()["prompts"] if p["kind"] == "interview")
        assert interview_after["source"] == "db"

    async def test_non_admin_is_403(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="prompt-user@example.com", role="user")
        response = await client.get("/api/admin/prompts", headers=auth_headers(user, test_settings))
        assert response.status_code == 403


class TestGetPrompt:
    async def test_unknown_kind_is_404(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/admin/prompts/does_not_exist", headers=admin_headers)
        assert response.status_code == 404

    async def test_non_admin_is_403(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="prompt-user2@example.com", role="user")
        response = await client.get(
            "/api/admin/prompts/interview", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403


class TestPutPrompt:
    async def test_put_then_get_reflects_the_override_and_primes_the_cache(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        put = await client.put(
            "/api/admin/prompts/interview", json={"content": "NEW"}, headers=admin_headers
        )
        assert put.status_code == 200
        assert put.json()["content"] == "NEW"
        assert put.json()["source"] == "db"

        get = await client.get("/api/admin/prompts/interview", headers=admin_headers)
        assert get.status_code == 200
        assert get.json()["content"] == "NEW"
        assert get.json()["source"] == "db"

        # The save must prime the in-process cache immediately (not only at
        # the next process start), since request-time code reads via
        # load_prompt(), not the repository.
        assert P.load_prompt("interview") == "NEW"

    async def test_put_missing_required_token_is_422(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.put(
            "/api/admin/prompts/interview_playbook",
            json={"content": "missing slots"},
            headers=admin_headers,
        )
        assert response.status_code == 422

    async def test_unknown_kind_is_404(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.put(
            "/api/admin/prompts/does_not_exist", json={"content": "x"}, headers=admin_headers
        )
        assert response.status_code == 404

    async def test_non_admin_is_403(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="prompt-user3@example.com", role="user")
        response = await client.put(
            "/api/admin/prompts/interview",
            json={"content": "NEW"},
            headers=auth_headers(user, test_settings),
        )
        assert response.status_code == 403


class TestDeletePrompt:
    async def test_delete_reverts_to_default(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        await client.put(
            "/api/admin/prompts/interview", json={"content": "NEW"}, headers=admin_headers
        )

        delete = await client.delete("/api/admin/prompts/interview", headers=admin_headers)
        assert delete.status_code == 204

        get = await client.get("/api/admin/prompts/interview", headers=admin_headers)
        assert get.json()["source"] == "file"
        assert get.json()["content"] != "NEW"

    async def test_unknown_kind_is_404(
        self, client: AsyncClient, admin_headers: dict[str, str]
    ) -> None:
        response = await client.delete("/api/admin/prompts/does_not_exist", headers=admin_headers)
        assert response.status_code == 404

    async def test_non_admin_is_403(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        user = await create_user(db_session, email="prompt-user4@example.com", role="user")
        response = await client.delete(
            "/api/admin/prompts/interview", headers=auth_headers(user, test_settings)
        )
        assert response.status_code == 403
