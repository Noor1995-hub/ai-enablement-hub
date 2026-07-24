"""POST /api/admin/users/{id}/reminder: the disabled/404 paths against the
default conftest client, plus sent/failed against a stub ACS sender (mirrors
test_admin_email.py's make_client wiring). The reminder template is a fixed
module constant (not per-project-customizable), so unlike invite/reset there
is no custom-template variant to cover here.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.core.dependencies.database import get_session
from src.core.dependencies.email import get_email_service
from src.core.dependencies.settings import get_settings
from src.main import app
from src.services.email_service import EmailSender, EmailService
from tests.fixtures.auth import auth_headers
from tests.fixtures.email import TEST_EMAIL, RaisingSender, RecordingSender
from tests.fixtures.factories import create_company, create_project, create_user

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import Project


@pytest_asyncio.fixture
async def make_client(
    db_session: AsyncSession, test_settings: Settings
) -> AsyncGenerator[Callable[[EmailSender], Awaitable[AsyncClient]]]:
    """Factory: conftest's client plus a REAL EmailService whose outbound leg
    is the given stub sender — copied from test_admin_email.py."""
    clients: list[AsyncClient] = []

    async def _make(sender: EmailSender) -> AsyncClient:
        async def _override_session() -> AsyncGenerator[AsyncSession]:
            yield db_session

        service = EmailService(sender, sender_address=TEST_EMAIL.sender_address)
        app.dependency_overrides[get_session] = _override_session
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_email_service] = lambda: service
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
        clients.append(client)
        return client

    try:
        yield _make
    finally:
        app.dependency_overrides.clear()
        for client in clients:
            await client.aclose()


@pytest_asyncio.fixture
async def project(db_session: AsyncSession) -> Project:
    company = await create_company(db_session, "Reminder Co")
    return await create_project(db_session, company, "Reminder Project")


@pytest_asyncio.fixture
async def headers(db_session: AsyncSession, test_settings: Settings) -> dict[str, str]:
    admin = await create_user(db_session, email="reminder-admin@example.com", role="admin")
    return auth_headers(admin, test_settings)


class TestReminder:
    async def test_disabled_when_email_unconfigured(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="r1@x.test", role="admin")
        learner = await create_user(db_session, email="r-l1@x.test")
        resp = await client.post(
            f"/api/admin/users/{learner.id}/reminder",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 200
        assert resp.json() == {"email_status": "disabled"}

    async def test_unknown_user_404(
        self, client: AsyncClient, db_session: AsyncSession, test_settings: Settings
    ) -> None:
        admin = await create_user(db_session, email="r2@x.test", role="admin")
        resp = await client.post(
            f"/api/admin/users/{uuid.uuid4()}/reminder",
            headers=auth_headers(admin, test_settings),
        )
        assert resp.status_code == 404


class TestReminderEmail:
    async def test_sent_includes_first_name_and_login_link(
        self,
        make_client: Callable[[EmailSender], Awaitable[AsyncClient]],
        headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        learner = await create_user(
            db_session, email="reminder-learner@example.com", first_name="Remy"
        )
        sender = RecordingSender()
        client = await make_client(sender)
        response = await client.post(f"/api/admin/users/{learner.id}/reminder", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"email_status": "sent"}
        [message] = sender.messages
        assert message["recipients"] == {"to": [{"address": "reminder-learner@example.com"}]}
        assert "Remy" in message["content"]["plainText"]
        assert "/login" in message["content"]["plainText"]

    async def test_sent_includes_project_suffix_when_assigned(
        self,
        make_client: Callable[[EmailSender], Awaitable[AsyncClient]],
        headers: dict[str, str],
        project: Project,
        db_session: AsyncSession,
    ) -> None:
        learner = await create_user(
            db_session,
            email="reminder-proj@example.com",
            first_name="Prue",
            project_id=project.id,
        )
        sender = RecordingSender()
        client = await make_client(sender)
        response = await client.post(f"/api/admin/users/{learner.id}/reminder", headers=headers)
        assert response.status_code == 200
        [message] = sender.messages
        assert f"for {project.name}" in message["content"]["plainText"]

    async def test_failed_send_still_returns_200(
        self,
        make_client: Callable[[EmailSender], Awaitable[AsyncClient]],
        headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        learner = await create_user(db_session, email="reminder-fail@example.com")
        client = await make_client(RaisingSender())
        response = await client.post(f"/api/admin/users/{learner.id}/reminder", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"email_status": "failed"}
