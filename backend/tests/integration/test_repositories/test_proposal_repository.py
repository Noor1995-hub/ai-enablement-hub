from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.db.models import Feedback, LessonContentProposal
from src.repositories.feedback_repository import FeedbackRepository
from src.repositories.proposal_repository import ProposalRepository
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


async def _seed(db_session: AsyncSession, name: str) -> tuple:
    company = await create_company(db_session, f"{name} Co")
    project = await create_project(db_session, company, f"{name} Project")
    user = await create_user(
        db_session, email=f"{name}@x.test", company_id=company.id, project_id=project.id
    )
    track = await create_track(db_session, f"{name} Track")
    module = await create_module(db_session, track, f"{name} Module")
    lesson = await create_lesson(
        db_session,
        module,
        f"{name} Lesson",
        content_blocks=[{"id": "b1", "type": "paragraph", "text": "Before."}],
    )
    return user, track, module, lesson


async def test_list_accepted_with_lesson_filters_and_joins(db_session: AsyncSession) -> None:
    user, _track, _module, lesson = await _seed(db_session, "accepted")
    accepted = Feedback(
        user_id=user.id, lesson_id=lesson.id, message="add an example", status="accepted"
    )
    db_session.add_all(
        [
            accepted,
            Feedback(user_id=user.id, lesson_id=lesson.id, message="new one"),
            Feedback(user_id=user.id, lesson_id=lesson.id, message="nope", status="dismissed"),
        ]
    )
    await db_session.commit()

    rows = await FeedbackRepository(db_session).list_accepted_with_lesson()

    assert [fb.id for fb, _lesson in rows] == [accepted.id]
    assert rows[0][1].id == lesson.id


async def test_list_by_ids_returns_only_the_requested_rows(db_session: AsyncSession) -> None:
    user, _track, _module, lesson = await _seed(db_session, "byids")
    wanted = Feedback(user_id=user.id, lesson_id=lesson.id, message="wanted")
    other = Feedback(user_id=user.id, lesson_id=lesson.id, message="other")
    db_session.add_all([wanted, other])
    await db_session.commit()

    rows = await FeedbackRepository(db_session).list_by_ids([wanted.id])

    assert [fb.message for fb in rows] == ["wanted"]
    assert await FeedbackRepository(db_session).list_by_ids([]) == []


async def test_covered_feedback_ids_counts_pending_approved_failed_only(
    db_session: AsyncSession,
) -> None:
    _user, _track, _module, lesson = await _seed(db_session, "covered")
    pending_id, approved_id, failed_id, rejected_id = (uuid.uuid4() for _ in range(4))
    for status, feedback_id in (
        ("pending", pending_id),
        ("approved", approved_id),
        ("failed", failed_id),
        ("rejected", rejected_id),
        ("superseded", uuid.uuid4()),
    ):
        db_session.add(
            LessonContentProposal(
                lesson_id=lesson.id,
                proposed_blocks=[],
                base_blocks=[],
                source_feedback_ids=[str(feedback_id)],
                summary=status,
                status=status,
            )
        )
    await db_session.commit()

    covered = await ProposalRepository(db_session).covered_feedback_ids()

    assert covered == {pending_id, approved_id, failed_id}


async def test_create_get_and_set_status(db_session: AsyncSession) -> None:
    user, _track, _module, lesson = await _seed(db_session, "lifecycle")
    repo = ProposalRepository(db_session)
    feedback_id = uuid.uuid4()

    created = await repo.create(
        lesson_id=lesson.id,
        proposed_blocks=[{"id": "b1", "type": "paragraph", "text": "After."}],
        base_blocks=lesson.content_blocks,
        source_feedback_ids=[feedback_id],
        summary="Reworded the opening.",
    )

    assert created.status == "pending"
    # uuids are stored as strings so the JSONB round-trip is lossless.
    assert created.source_feedback_ids == [str(feedback_id)]

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None

    await repo.set_status(fetched, "approved", user.id)
    await db_session.refresh(fetched)
    assert fetched.status == "approved"
    assert fetched.reviewed_by == user.id
    assert fetched.reviewed_at is not None

    assert await repo.get_by_id(uuid.uuid4()) is None


async def test_list_admin_joins_context_and_filters_by_status(db_session: AsyncSession) -> None:
    _user, track, module, lesson = await _seed(db_session, "listadmin")
    repo = ProposalRepository(db_session)
    await repo.create(
        lesson_id=lesson.id,
        proposed_blocks=[],
        base_blocks=[],
        source_feedback_ids=[],
        summary="first",
    )

    rows = await repo.list_admin(status="pending", limit=10, offset=0)

    assert len(rows) == 1
    proposal, lesson_title, module_title, track_id, track_name, track_level = rows[0]
    assert proposal.summary == "first"
    assert lesson_title == lesson.title
    assert module_title == module.title
    assert track_id == track.id
    assert track_name == track.name
    assert track_level == track.required_level
    assert await repo.count_admin(status="pending") == 1
    assert await repo.count_admin(status="approved") == 0
    assert await repo.count_admin(status=None) == 1


async def test_set_approved_without_edits_leaves_edited_blocks_null(
    db_session: AsyncSession,
) -> None:
    user, _track, _module, lesson = await _seed(db_session, "approve-plain")
    repo = ProposalRepository(db_session)
    created = await repo.create(
        lesson_id=lesson.id,
        proposed_blocks=[{"id": "b1", "type": "paragraph", "text": "Agent."}],
        base_blocks=lesson.content_blocks,
        source_feedback_ids=[],
        summary="s",
    )

    await repo.set_approved(created, edited_blocks=None, reviewed_by=user.id)
    await db_session.refresh(created)

    assert created.status == "approved"
    assert created.edited_blocks is None
    assert created.reviewed_by == user.id
    assert created.reviewed_at is not None


async def test_set_approved_with_edits_stores_the_admin_array(
    db_session: AsyncSession,
) -> None:
    user, _track, _module, lesson = await _seed(db_session, "approve-edited")
    repo = ProposalRepository(db_session)
    created = await repo.create(
        lesson_id=lesson.id,
        proposed_blocks=[{"id": "b1", "type": "paragraph", "text": "Agent."}],
        base_blocks=lesson.content_blocks,
        source_feedback_ids=[],
        summary="s",
    )
    admin_blocks = [{"id": "b1", "type": "paragraph", "text": "Admin."}]

    await repo.set_approved(created, edited_blocks=admin_blocks, reviewed_by=user.id)
    await db_session.refresh(created)

    assert created.status == "approved"
    assert created.edited_blocks == admin_blocks
    # The agent's own draft is never overwritten by the admin's version.
    assert created.proposed_blocks == [{"id": "b1", "type": "paragraph", "text": "Agent."}]


async def test_set_critique_stamps_the_columns(db_session: AsyncSession) -> None:
    _user, _track, _module, lesson = await _seed(db_session, "critique-store")
    repo = ProposalRepository(db_session)
    created = await repo.create(
        lesson_id=lesson.id,
        proposed_blocks=[],
        base_blocks=[],
        source_feedback_ids=[],
        summary="s",
    )

    await repo.set_critique(
        created, agent_wrong="I used a card group.", admin_preferred="Inline bullets."
    )
    await db_session.refresh(created)

    assert created.critique_agent_wrong == "I used a card group."
    assert created.critique_admin_preferred == "Inline bullets."
    assert created.critiqued_at is not None
