# backend/tests/integration/test_repositories/test_org_repository.py
from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.org_repository import OrgRepository
from tests.fixtures.factories import create_company, create_project

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_get_ai_settings_empty_by_default(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "Org Repo AI Co")
    project = await create_project(db_session, company, "Org Repo AI Project")
    repo = OrgRepository(db_session)

    assert await repo.get_ai_settings(project.id) == []


async def test_upsert_ai_setting_then_get(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "Org Repo AI Co 2")
    project = await create_project(db_session, company, "Org Repo AI Project 2")
    repo = OrgRepository(db_session)

    await repo.upsert_ai_setting(project.id, "chatbot", enabled=True)
    rows = await repo.get_ai_settings(project.id)

    assert len(rows) == 1
    assert rows[0].kind == "chatbot"
    assert rows[0].enabled is True

    # upsert again flips it, doesn't duplicate the row
    await repo.upsert_ai_setting(project.id, "chatbot", enabled=False)
    rows = await repo.get_ai_settings(project.id)
    assert len(rows) == 1
    assert rows[0].enabled is False
