"""Bulk invite: the AdminUserService helpers (this file's TestBulkInviteService)
and the POST /api/admin/invites/bulk endpoint (added in a later task). The
service is wired to the test session directly, mirroring conftest's
token_service fixture."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.core.dependencies.database import get_session
from src.core.dependencies.email import get_email_service
from src.core.dependencies.settings import get_settings
from src.db.models import ProjectTrackDefault, User, UserLesson, UserModule, UserTrack
from src.main import app
from src.repositories.assignment_repository import AssignmentRepository
from src.repositories.auth_session_repository import AuthSessionRepository
from src.repositories.content_repository import ContentRepository
from src.repositories.org_repository import OrgRepository
from src.repositories.progress_repository import ProgressRepository
from src.repositories.survey_repository import SurveyRepository
from src.repositories.user_repository import UserRepository
from src.services.admin_user_service import AdminUserService
from src.services.email_service import EmailSender, EmailService
from src.services.exceptions import NotFoundError
from tests.fixtures.auth import auth_headers
from tests.fixtures.email import TEST_EMAIL, RaisingSender, RecordingSender
from tests.fixtures.factories import (
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def admin_user_service(db_session: AsyncSession) -> AdminUserService:
    return AdminUserService(
        UserRepository(db_session),
        OrgRepository(db_session),
        AssignmentRepository(db_session),
        ContentRepository(db_session),
        SurveyRepository(db_session),
        AuthSessionRepository(db_session),
        ProgressRepository(db_session),
    )


class TestBulkInviteService:
    async def test_existing_emails_returns_only_known(
        self, db_session: AsyncSession, admin_user_service: AdminUserService
    ) -> None:
        await create_user(db_session, email="known@acme.be")
        result = await admin_user_service.existing_emails(["known@acme.be", "new@acme.be"])
        assert result == {"known@acme.be"}

    async def test_existing_emails_empty_input(self, admin_user_service: AdminUserService) -> None:
        assert await admin_user_service.existing_emails([]) == set()

    async def test_ensure_project_unknown_raises(
        self, admin_user_service: AdminUserService
    ) -> None:
        with pytest.raises(NotFoundError):
            await admin_user_service.ensure_project(uuid.uuid4())

    async def test_create_invited_users_creates_and_binds_project(
        self, db_session: AsyncSession, admin_user_service: AdminUserService
    ) -> None:
        company = await create_company(db_session, "Bulk Co")
        project = await create_project(db_session, company, "Bulk Project")
        created = await admin_user_service.create_invited_users(
            project.id,
            [("Jan", "Peeters", "jan@acme.be"), ("Sofie", "Maes", "sofie@acme.be")],
        )
        assert {u.email for u in created} == {"jan@acme.be", "sofie@acme.be"}
        assert all(u.project_id == project.id for u in created)
        assert all(u.company_id == company.id for u in created)
        assert all(u.role == "user" and u.password_set is False for u in created)

    async def test_create_invited_users_skips_now_existing(
        self, db_session: AsyncSession, admin_user_service: AdminUserService
    ) -> None:
        company = await create_company(db_session, "Bulk Co2")
        project = await create_project(db_session, company, "Bulk Project2")
        await create_user(db_session, email="taken@acme.be")
        created = await admin_user_service.create_invited_users(
            project.id,
            [("Taken", "User", "taken@acme.be"), ("Fresh", "User", "fresh@acme.be")],
        )
        assert {u.email for u in created} == {"fresh@acme.be"}

    async def test_create_invited_users_unknown_project_raises(
        self, admin_user_service: AdminUserService
    ) -> None:
        with pytest.raises(NotFoundError):
            await admin_user_service.create_invited_users(uuid.uuid4(), [("A", "B", "a@b.co")])


_CSV = (
    "first_name,last_name,email\n"
    "Jan,Peeters,jan@acme.be\n"
    "Sofie,Maes,sofie@acme.be\n"
    ",Bad,bad@acme.be\n"  # invalid: missing first name
)


def _extract_invite_token(text: str) -> str:
    assert "/invite/" in text
    return text.rsplit("/invite/", 1)[1].split()[0].strip()


@pytest_asyncio.fixture
async def make_email_client(
    db_session: AsyncSession,
    test_settings,
) -> AsyncGenerator[Callable[[EmailSender], Awaitable[AsyncClient]]]:
    """conftest's client + the ACS transport stubbed; EmailTemplateService
    resolves + renders for real against the (overridden) test session."""
    clients: list[AsyncClient] = []

    async def _make(sender: EmailSender) -> AsyncClient:
        async def _override_session() -> AsyncGenerator[AsyncSession]:
            yield db_session

        service = EmailService(sender, sender_address=TEST_EMAIL.sender_address)
        app.dependency_overrides[get_session] = _override_session
        app.dependency_overrides[get_settings] = lambda: test_settings
        app.dependency_overrides[get_email_service] = lambda: service
        c = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
        clients.append(c)
        return c

    try:
        yield _make
    finally:
        app.dependency_overrides.clear()
        for c in clients:
            await c.aclose()


@pytest_asyncio.fixture
async def project(db_session: AsyncSession):
    company = await create_company(db_session, "Bulk Endpoint Co")
    return await create_project(db_session, company, "Bulk Endpoint Project")


@pytest_asyncio.fixture
async def headers(db_session: AsyncSession, test_settings) -> dict[str, str]:
    admin = await create_user(db_session, email="bulk-admin@example.com", role="admin")
    return auth_headers(admin, test_settings)


async def _upload(client, csv_text, project_id, *, dry_run, headers):
    return await client.post(
        "/api/admin/invites/bulk",
        files={"file": ("roster.csv", csv_text.encode("utf-8"), "text/csv")},
        data={"project_id": str(project_id), "dry_run": str(dry_run).lower()},
        headers=headers,
    )


class TestBulkInviteEndpoint:
    async def test_dry_run_previews_and_creates_nothing(
        self,
        make_email_client,
        project,
        headers,
        db_session,
    ) -> None:
        await create_user(db_session, email="sofie@acme.be")  # seeded duplicate
        sender = RecordingSender()
        client = await make_email_client(sender)
        resp = await _upload(client, _CSV, project.id, dry_run=True, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["dry_run"] is True
        s = data["summary"]
        assert (s["valid"], s["duplicates"], s["invalid"], s["created"]) == (1, 1, 1, 0)
        assert sender.messages == []
        listing = await client.get(f"/api/admin/users?project_id={project.id}", headers=headers)
        assert listing.json()["users"] == []  # nothing created in this project

    async def test_commit_creates_and_emails_valid_rows(
        self,
        make_email_client,
        project,
        headers,
        db_session,
    ) -> None:
        await create_user(db_session, email="sofie@acme.be")  # duplicate → skipped
        sender = RecordingSender()
        client = await make_email_client(sender)
        resp = await _upload(client, _CSV, project.id, dry_run=False, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        s = data["summary"]
        assert (s["created"], s["duplicates"], s["invalid"], s["email_failed"]) == (1, 1, 1, 0)
        [message] = sender.messages
        assert message["recipients"] == {"to": [{"address": "jan@acme.be"}]}
        # The emailed invite link is redeemable.
        info = await client.get(
            f"/api/auth/invite/{_extract_invite_token(message['content']['plainText'])}"
        )
        assert info.status_code == 200
        assert info.json()["purpose"] == "invite"
        # The created user now shows up in the project listing.
        listing = await client.get(f"/api/admin/users?project_id={project.id}", headers=headers)
        assert [u["email"] for u in listing.json()["users"]] == ["jan@acme.be"]

    async def test_failed_email_marks_row_but_still_creates_user(
        self,
        make_email_client,
        project,
        headers,
    ) -> None:
        client = await make_email_client(RaisingSender())
        csv_text = "first_name,last_name,email\nOnly,One,only@acme.be\n"
        resp = await _upload(client, csv_text, project.id, dry_run=False, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["email_failed"] == 1
        assert data["summary"]["created"] == 0
        row = next(r for r in data["rows"] if r["email"] == "only@acme.be")
        assert row["status"] == "email_failed"
        listing = await client.get(f"/api/admin/users?project_id={project.id}", headers=headers)
        assert [u["email"] for u in listing.json()["users"]] == ["only@acme.be"]

    async def test_email_disabled_still_creates_users(
        self,
        client: AsyncClient,
        project,
        headers,
    ) -> None:
        """Default conftest client has email=None (disabled): commit still
        creates the users and reports them as created."""
        csv_text = "first_name,last_name,email\nNo,Mail,nomail@acme.be\n"
        resp = await _upload(client, csv_text, project.id, dry_run=False, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["summary"]["created"] == 1

    async def test_oversize_file_is_413(self, client: AsyncClient, project, headers) -> None:
        big = "first_name,last_name,email\n" + ("x" * 1_048_600) + "\n"
        resp = await _upload(client, big, project.id, dry_run=True, headers=headers)
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "payload_too_large"

    async def test_too_many_rows_is_400(self, client: AsyncClient, project, headers) -> None:
        body = "first_name,last_name,email\n" + "".join(
            f"F{i},L{i},user{i}@acme.be\n" for i in range(201)
        )
        resp = await _upload(client, body, project.id, dry_run=True, headers=headers)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "bad_request"

    async def test_missing_column_is_400(self, client: AsyncClient, project, headers) -> None:
        resp = await _upload(
            client, "first_name,email\nJan,jan@acme.be\n", project.id, dry_run=True, headers=headers
        )
        assert resp.status_code == 400

    async def test_unknown_project_is_404(self, client: AsyncClient, headers) -> None:
        resp = await _upload(client, _CSV, uuid.uuid4(), dry_run=True, headers=headers)
        assert resp.status_code == 404

    async def test_requires_authentication(self, client: AsyncClient, project) -> None:
        resp = await _upload(client, _CSV, project.id, dry_run=True, headers={})
        assert resp.status_code == 401

    async def test_requires_admin(
        self,
        client: AsyncClient,
        project,
        db_session,
        test_settings,
    ) -> None:
        member = await create_user(db_session, email="bulk-member@example.com", role="user")
        resp = await _upload(
            client, _CSV, project.id, dry_run=True, headers=auth_headers(member, test_settings)
        )
        assert resp.status_code == 403

    async def test_commit_materializes_project_defaults_for_created_users(
        self,
        client: AsyncClient,
        project,
        headers,
        db_session,
    ) -> None:
        """A project with a default track: every user created via the bulk CSV
        path gets that track (+ its modules/lessons) materialized with
        assigned_via='default', same as the single-invite path."""
        track = await create_track(db_session)
        module = await create_module(db_session, track)
        lesson = await create_lesson(db_session, module)
        db_session.add(ProjectTrackDefault(project_id=project.id, track_id=track.id))
        await db_session.commit()
        csv_text = "first_name,last_name,email\nDef,Ault,defaulted@acme.be\n"
        resp = await _upload(client, csv_text, project.id, dry_run=False, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["summary"]["created"] == 1

        user = (
            await db_session.execute(select(User).where(User.email == "defaulted@acme.be"))
        ).scalar_one()
        track_rows = (
            (await db_session.execute(select(UserTrack).where(UserTrack.user_id == user.id)))
            .scalars()
            .all()
        )
        assert {(r.track_id, r.assigned_via) for r in track_rows} == {(track.id, "default")}
        module_rows = (
            (await db_session.execute(select(UserModule).where(UserModule.user_id == user.id)))
            .scalars()
            .all()
        )
        assert {(r.module_id, r.assigned_via) for r in module_rows} == {(module.id, "default")}
        lesson_rows = (
            (await db_session.execute(select(UserLesson).where(UserLesson.user_id == user.id)))
            .scalars()
            .all()
        )
        assert {(r.lesson_id, r.assigned_via) for r in lesson_rows} == {(lesson.id, "default")}
