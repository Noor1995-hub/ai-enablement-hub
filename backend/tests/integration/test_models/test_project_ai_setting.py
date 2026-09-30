from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.db.models import ProjectAiSetting
from src.repositories.org_repository import OrgRepository
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


async def test_stamps_created_and_updated_at(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "AI Setting Timestamps Co")
    project = await create_project(db_session, company, "AI Setting Timestamps Project")

    setting = ProjectAiSetting(project_id=project.id, kind="chatbot")
    db_session.add(setting)
    await db_session.commit()
    await db_session.refresh(setting)

    assert setting.created_at is not None
    assert setting.updated_at is not None


async def test_ai_setting_second_upsert_advances_updated_at(db_session: AsyncSession) -> None:
    """`upsert_ai_setting` writes through a raw `ON CONFLICT DO UPDATE`, which
    never fires `onupdate=func.now()` — only columns named in `set_` move. The
    whole test runs inside one outer transaction, so `func.now()` is constant
    throughout it; comparing two calls to it would pass even with the bug.
    Backdating to a literal timestamp first gives something distinct from
    "now" to compare against, so this fails if `updated_at` is dropped from
    `set_`.
    """
    company = await create_company(db_session, "AI Setting Advance Co")
    project = await create_project(db_session, company, "AI Setting Advance Project")
    repo = OrgRepository(db_session)
    await repo.upsert_ai_setting(project.id, "chatbot", enabled=True)

    [setting] = await repo.get_ai_settings(project.id)
    backdated = datetime(2000, 1, 1, tzinfo=UTC)
    setting.updated_at = backdated
    await db_session.commit()

    await repo.upsert_ai_setting(project.id, "chatbot", enabled=False)
    await db_session.refresh(setting)

    assert setting.updated_at > backdated


async def test_component_setting_second_upsert_advances_updated_at(
    db_session: AsyncSession,
) -> None:
    """Same latent bug as `upsert_ai_setting`, on the sibling
    `ProjectComponentSetting.updated_at` (which predates this migration)."""
    company = await create_company(db_session, "Component Setting Advance Co")
    project = await create_project(db_session, company, "Component Setting Advance Project")
    repo = OrgRepository(db_session)
    await repo.upsert_component_setting(project.id, "learning", hidden=False, locked=False)

    [setting] = await repo.get_component_settings(project.id)
    backdated = datetime(2000, 1, 1, tzinfo=UTC)
    setting.updated_at = backdated
    await db_session.commit()

    await repo.upsert_component_setting(project.id, "learning", hidden=True, locked=False)
    await db_session.refresh(setting)

    assert setting.updated_at > backdated
