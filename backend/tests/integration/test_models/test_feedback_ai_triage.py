from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError

from src.db.models import Feedback
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def _feedback(db_session: AsyncSession, email: str) -> Feedback:
    user = await create_user(db_session, email=email)
    track = await create_track(db_session, "Triage Track")
    module = await create_module(db_session, track, "Triage Module")
    lesson = await create_lesson(db_session, module, "Triage Lesson")
    row = Feedback(user_id=user.id, lesson_id=lesson.id, message="The examples were unclear")
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


async def test_ai_columns_default_to_null(db_session: AsyncSession) -> None:
    row = await _feedback(db_session, "triage-model-1@x.test")

    assert row.ai_suggested_status is None
    assert row.ai_rationale is None
    assert row.ai_suggested_at is None
    # An un-suggested row is still a normal `new` row.
    assert row.status == "new"


async def test_suggestion_persists_without_touching_status(db_session: AsyncSession) -> None:
    row = await _feedback(db_session, "triage-model-2@x.test")

    row.ai_suggested_status = "accepted"
    row.ai_rationale = "Asks for a concrete example in the prompting section."
    row.ai_suggested_at = datetime.now(UTC)
    await db_session.commit()
    await db_session.refresh(row)

    assert row.ai_suggested_status == "accepted"
    assert row.ai_rationale == "Asks for a concrete example in the prompting section."
    assert row.ai_suggested_at is not None
    assert row.status == "new"
    assert row.reviewed_by is None
    assert row.reviewed_at is None


async def test_unknown_suggested_status_is_rejected(db_session: AsyncSession) -> None:
    row = await _feedback(db_session, "triage-model-3@x.test")

    row.ai_suggested_status = "maybe"
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
