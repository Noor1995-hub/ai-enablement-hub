from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.db.models import LessonContentProposal, Project, User
from src.repositories.content_repository import ContentRepository
from src.repositories.org_repository import OrgRepository
from src.repositories.project_admin_repository import ProjectAdminRepository
from src.repositories.proposal_repository import ProposalRepository
from src.repositories.unit_of_work import UnitOfWork
from src.repositories.user_repository import UserRepository
from tests.fixtures.factories import (
    create_company,
    create_lesson,
    create_module,
    create_project,
    create_track,
    create_user,
    make_project_admin,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_members_of_projects_and_company(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "B6 Repo Co")
    p1 = await create_project(db_session, company, "B6 P1")
    other = await create_project(
        db_session, await create_company(db_session, "B6 Other Co"), "B6 P2"
    )
    in_p1 = await create_user(
        db_session, email="b6-in-p1@example.com", company_id=company.id, project_id=p1.id
    )
    company_only = await create_user(db_session, email="b6-co@example.com", company_id=company.id)
    await create_user(db_session, email="b6-out@example.com", project_id=other.id)
    repo = UserRepository(db_session)

    assert {u.id for u in await repo.members_of([p1.id], None)} == {in_p1.id}
    assert {u.id for u in await repo.members_of([p1.id], company.id)} == {in_p1.id, company_only.id}


async def test_stage_set_org_and_delete_many(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "B6 Stage Co")
    project = await create_project(db_session, company, "B6 Stage P")
    a = await create_user(db_session, email="b6-a@example.com", project_id=project.id)
    b = await create_user(db_session, email="b6-b@example.com", project_id=project.id)
    repo = UserRepository(db_session)

    await repo.stage_set_org([a.id], None, None)
    await repo.stage_delete_many([b.id])
    await UnitOfWork(db_session).commit()

    rows = {
        u.id: u
        for u in (await db_session.execute(select(User).where(User.id.in_([a.id, b.id])))).scalars()
    }
    await db_session.refresh(rows[a.id])
    assert rows[a.id].project_id is None
    assert b.id not in rows


async def test_org_rename_and_stage_delete(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "B6 Rename Co")
    project = await create_project(db_session, company, "Old name")
    repo = OrgRepository(db_session)

    renamed = await repo.rename_project(project, "New name")
    assert renamed.name == "New name"
    await repo.stage_delete_company(company)
    await UnitOfWork(db_session).commit()

    assert (
        await db_session.execute(select(Project).where(Project.id == project.id))
    ).scalar_one_or_none() is None


async def test_stage_revoke(db_session: AsyncSession) -> None:
    company = await create_company(db_session, "B6 Grant Co")
    project = await create_project(db_session, company, "B6 Grant P")
    coach = await create_user(db_session, email="b6-coach@example.com")
    await make_project_admin(db_session, coach, project)
    repo = ProjectAdminRepository(db_session)

    await repo.stage_revoke(coach.id, project.id)
    await UnitOfWork(db_session).commit()

    assert not await repo.is_project_admin(coach.id)


async def test_lessons_with_module_titles_and_live_proposal_blocks(
    db_session: AsyncSession,
) -> None:
    module = await create_module(db_session, await create_track(db_session), "B6 Module")
    lesson = await create_lesson(db_session, module, "B6 Lesson")
    blocks = [{"id": "i", "type": "image", "blob_path": "images/x.png", "alt": "a"}]
    for status in ("pending", "rejected"):
        db_session.add(
            LessonContentProposal(
                lesson_id=lesson.id,
                proposed_blocks=blocks,
                base_blocks=[],
                status=status,
                source_feedback_ids=[],
                summary="s",
            )
        )
    await db_session.commit()

    rows = await ContentRepository(db_session).lessons_with_module_titles()
    assert any(le.id == lesson.id and title == "B6 Module" for le, title in rows)
    sets = await ProposalRepository(db_session).live_block_sets()
    assert blocks in sets
    assert sets.count(blocks) == 1  # the rejected proposal is not live
