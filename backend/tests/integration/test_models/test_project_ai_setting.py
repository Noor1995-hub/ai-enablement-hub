from __future__ import annotations

from typing import TYPE_CHECKING

from src.db.models import ProjectAiSetting
from tests.fixtures.factories import create_company, create_project

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_defaults_to_disabled(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "AI Setting Co")
    project = await create_project(db_session, company, "AI Setting Project")

    setting = ProjectAiSetting(project_id=project.id, kind="chatbot")
    db_session.add(setting)
    await db_session.commit()
    await db_session.refresh(setting)

    assert setting.enabled is False
