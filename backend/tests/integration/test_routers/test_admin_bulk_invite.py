"""Bulk invite: the AdminUserService helpers (this file's TestBulkInviteService)
and the POST /api/admin/invites/bulk endpoint (added in a later task). The
service is wired to the test session directly, mirroring conftest's
token_service fixture."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

from src.repositories.assignment_repository import AssignmentRepository
from src.repositories.content_repository import ContentRepository
from src.repositories.org_repository import OrgRepository
from src.repositories.survey_repository import SurveyRepository
from src.repositories.user_repository import UserRepository
from src.services.admin_user_service import AdminUserService
from src.services.exceptions import NotFoundError
from tests.fixtures.factories import create_company, create_project, create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
def admin_user_service(db_session: AsyncSession) -> AdminUserService:
    return AdminUserService(
        UserRepository(db_session),
        OrgRepository(db_session),
        AssignmentRepository(db_session),
        ContentRepository(db_session),
        SurveyRepository(db_session),
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
