"""The two flows that must be all-or-nothing: assessment completion and
proposal approval. Both used to commit each step separately.

The harness binds every test to one outer transaction and turns an application
`commit()` into a savepoint release (conftest.py, join_transaction_mode), so a
second connection can never see anything a test writes. "Not committed yet" is
therefore checked the way the harness allows: `session.rollback()` discards
exactly the work since the last commit, so a staged write that survives a
rollback was committed by someone, and one that vanishes was not.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from src.db.models import (
    Lesson,
    LessonContentProposal,
    SurveyResponse,
    UserLesson,
    UserModule,
    UserTrack,
)
from src.repositories.assignment_repository import AssignmentRepository
from src.repositories.calibration_note_repository import CalibrationNoteRepository
from src.repositories.content_repository import ContentRepository
from src.repositories.feedback_repository import FeedbackRepository
from src.repositories.proposal_repository import ProposalRepository
from src.repositories.survey_repository import SurveyRepository
from src.repositories.unit_of_work import UnitOfWork
from src.services.content_improvement_service import ContentImprovementService
from src.services.survey_service import SurveyService
from tests.fixtures.factories import (
    VALID_ANSWERS,
    create_lesson,
    create_module,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def _count(db_session: AsyncSession, model: Any, user_id: uuid.UUID) -> int:
    result = await db_session.execute(
        select(func.count()).select_from(model).where(model.user_id == user_id)
    )
    return result.scalar_one()


async def _boom(*args: object, **kwargs: object) -> None:
    raise RuntimeError("connection reset")


async def test_staged_assignment_writes_are_not_committed_until_the_uow_commits(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await create_user(db_session, email="uow-stage@example.com")
    track = await create_track(db_session, "UoW Track")
    # Captured now: a rollback expires every instance, and reloading an
    # expired attribute outside a greenlet-aware call would fail.
    user_id, track_id = user.id, track.id
    assignments = AssignmentRepository(db_session)
    uow = UnitOfWork(db_session)

    real_commit = db_session.commit
    commits: list[None] = []

    async def _spy_commit() -> None:
        commits.append(None)
        await real_commit()

    monkeypatch.setattr(db_session, "commit", _spy_commit)

    # Staged, then rolled back: the row is gone, so staging never committed.
    await assignments.stage_user_tracks(user_id, [track_id], True)
    assert commits == []
    assert await _count(db_session, UserTrack, user_id) == 1  # flushed, visible in-session
    await db_session.rollback()
    assert await _count(db_session, UserTrack, user_id) == 0

    # Staged, committed through the UoW, then rolled back: the row survives.
    await assignments.stage_user_tracks(user_id, [track_id], True)
    assert commits == []
    await uow.commit()
    assert len(commits) == 1
    await db_session.rollback()
    assert await _count(db_session, UserTrack, user_id) == 1


async def test_a_failing_seed_write_rolls_back_the_whole_completion(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One transaction: if the last staged write fails, the survey must NOT be
    scored and no partial assignment rows may survive."""
    user = await create_user(db_session, email="uow-atomic@example.com")
    user_id = user.id
    track = await create_track(db_session, "Atomic Track", required_level="explore")
    module = await create_module(db_session, track, "Atomic Module")
    await create_lesson(db_session, module, "Atomic Lesson")
    surveys = SurveyRepository(db_session)
    draft = await surveys.create_or_update(user_id, {"status": "in_progress", **VALID_ANSWERS})
    assert draft is not None

    assignments = AssignmentRepository(db_session)
    service = SurveyService(
        surveys, ContentRepository(db_session), assignments, UnitOfWork(db_session)
    )
    # Force the final staged write (tracks are written last) to fail, after
    # the module and lesson writes have already been flushed.
    monkeypatch.setattr(assignments, "stage_user_tracks", _boom)

    with pytest.raises(RuntimeError):
        await service.complete(user_id)
    await db_session.rollback()

    for model in (UserTrack, UserModule, UserLesson):
        assert await _count(db_session, model, user_id) == 0, (
            f"{model.__tablename__} kept a partial row"
        )
    row = (
        await db_session.execute(select(SurveyResponse).where(SurveyResponse.user_id == user_id))
    ).scalar_one()
    assert row.status == "in_progress"
    assert row.score_level is None


async def test_a_failing_approval_stamp_rolls_back_the_lesson_rewrite(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lesson rewrite and the proposal's approved stamp land together or not
    at all: a lesson rewritten under a still-`pending` proposal is what made a
    re-approve mis-report "superseded"."""
    reviewer = await create_user(db_session, email="uow-approve@example.com")
    reviewer_id = reviewer.id
    track = await create_track(db_session, "Approve Track")
    module = await create_module(db_session, track, "Approve Module")
    before = [{"id": "b1", "type": "paragraph", "text": "Before."}]
    lesson = await create_lesson(db_session, module, "Approve Lesson", content_blocks=before)
    lesson_id = lesson.id
    proposals = ProposalRepository(db_session)
    proposal = await proposals.create(
        lesson_id=lesson_id,
        proposed_blocks=[{"id": "b1", "type": "paragraph", "text": "Agent."}],
        base_blocks=before,
        source_feedback_ids=[],
        summary="s",
    )
    proposal_id = proposal.id

    service = ContentImprovementService(
        proposals,
        FeedbackRepository(db_session),
        ContentRepository(db_session),
        AsyncMock(),  # the review path never calls the model
        CalibrationNoteRepository(db_session),
        UnitOfWork(db_session),
    )
    # The lesson rewrite is staged first; fail the stamp that follows it.
    monkeypatch.setattr(proposals, "stage_approved", _boom)

    with pytest.raises(RuntimeError):
        await service.review(
            proposal_id=proposal_id,
            decision="approve",
            reviewer_id=reviewer_id,
            edited_blocks=[{"id": "b1", "type": "paragraph", "text": "Admin."}],
        )
    await db_session.rollback()

    stored_lesson = (
        await db_session.execute(select(Lesson).where(Lesson.id == lesson_id))
    ).scalar_one()
    assert stored_lesson.content_blocks == before
    stored_proposal = (
        await db_session.execute(
            select(LessonContentProposal).where(LessonContentProposal.id == proposal_id)
        )
    ).scalar_one()
    assert stored_proposal.status == "pending"
