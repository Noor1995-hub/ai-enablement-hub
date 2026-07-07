"""Invite/reset endpoints × email delivery: real EmailService (templates and
all) wired to a stub sender via dependency_overrides. Covers "sent" and
"failed" (endpoint still succeeds, token still redeemable); the "disabled"
path is asserted in test_admin_users.py against the default conftest client.
"""

from __future__ import annotations

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


def _extract_token(link: str) -> str:
    assert "/invite/" in link
    return link.rsplit("/invite/", 1)[1]


@pytest_asyncio.fixture
async def make_client(
    db_session: AsyncSession, test_settings: Settings
) -> AsyncGenerator[Callable[[EmailSender], Awaitable[AsyncClient]]]:
    """Factory: conftest's client plus a REAL EmailService (service + templates
    exercised end to end) whose outbound leg is the given stub sender."""
    clients: list[AsyncClient] = []

    async def _make(sender: EmailSender) -> AsyncClient:
        async def _override_session() -> AsyncGenerator[AsyncSession]:
            yield db_session

        service = EmailService(
            sender,
            sender_address=TEST_EMAIL.sender_address,
            app_url=test_settings.app.url,
            entra_enabled=False,
            invite_ttl_days=test_settings.auth.invite_ttl_days,
            reset_ttl_days=test_settings.auth.reset_ttl_days,
        )
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
    company = await create_company(db_session, "Mail Co")
    return await create_project(db_session, company, "Mail Project")


@pytest_asyncio.fixture
async def headers(db_session: AsyncSession, test_settings: Settings) -> dict[str, str]:
    admin = await create_user(db_session, email="mail-admin@example.com", role="admin")
    return auth_headers(admin, test_settings)


class TestInviteEmails:
    async def test_sent_and_addressed_with_the_returned_link(
        self,
        make_client: Callable[[EmailSender], Awaitable[AsyncClient]],
        project: Project,
        headers: dict[str, str],
    ) -> None:
        sender = RecordingSender()
        client = await make_client(sender)
        response = await client.post(
            "/api/admin/invites",
            json={
                "email": "newbie@example.com",
                "first_name": "New",
                "last_name": "Bie",
                "project_id": str(project.id),
            },
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email_status"] == "sent"
        [message] = sender.messages
        assert message["senderAddress"] == TEST_EMAIL.sender_address
        assert message["recipients"] == {"to": [{"address": "newbie@example.com"}]}
        assert data["link"] in message["content"]["plainText"]
        assert data["link"] in message["content"]["html"]

    async def test_failed_send_still_creates_a_redeemable_invite(
        self,
        make_client: Callable[[EmailSender], Awaitable[AsyncClient]],
        project: Project,
        headers: dict[str, str],
    ) -> None:
        client = await make_client(RaisingSender())
        response = await client.post(
            "/api/admin/invites",
            json={
                "email": "unlucky@example.com",
                "first_name": "Un",
                "last_name": "Lucky",
                "project_id": str(project.id),
            },
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email_status"] == "failed"
        # The manual copy-the-link fallback must remain fully usable.
        info = await client.get(f"/api/auth/invite/{_extract_token(data['link'])}")
        assert info.status_code == 200
        assert info.json()["purpose"] == "invite"

    async def test_send_email_false_skips_the_send_entirely(
        self,
        make_client: Callable[[EmailSender], Awaitable[AsyncClient]],
        project: Project,
        headers: dict[str, str],
    ) -> None:
        """The "Create invite link" admin action: even with EMAIL__* configured,
        no send is attempted and the link is still returned + redeemable."""
        sender = RecordingSender()
        client = await make_client(sender)
        response = await client.post(
            "/api/admin/invites",
            json={
                "email": "link-only@example.com",
                "first_name": "Link",
                "last_name": "Only",
                "project_id": str(project.id),
                "send_email": False,
            },
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email_status"] == "skipped"
        assert sender.messages == []
        info = await client.get(f"/api/auth/invite/{_extract_token(data['link'])}")
        assert info.status_code == 200
        assert info.json()["purpose"] == "invite"


class TestResetEmails:
    async def test_sent_and_addressed_with_the_returned_link(
        self,
        make_client: Callable[[EmailSender], Awaitable[AsyncClient]],
        db_session: AsyncSession,
        headers: dict[str, str],
    ) -> None:
        user = await create_user(db_session, email="resettee@example.com", first_name="Res")
        sender = RecordingSender()
        client = await make_client(sender)
        response = await client.post(f"/api/admin/users/{user.id}/reset-link", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email_status"] == "sent"
        [message] = sender.messages
        assert message["recipients"] == {"to": [{"address": "resettee@example.com"}]}
        assert "reset" in message["content"]["subject"].lower()
        assert data["link"] in message["content"]["plainText"]

    async def test_failed_send_still_returns_a_redeemable_link(
        self,
        make_client: Callable[[EmailSender], Awaitable[AsyncClient]],
        db_session: AsyncSession,
        headers: dict[str, str],
    ) -> None:
        user = await create_user(db_session, email="unlucky-reset@example.com")
        client = await make_client(RaisingSender())
        response = await client.post(f"/api/admin/users/{user.id}/reset-link", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email_status"] == "failed"
        info = await client.get(f"/api/auth/invite/{_extract_token(data['link'])}")
        assert info.status_code == 200
        assert info.json()["purpose"] == "reset"
