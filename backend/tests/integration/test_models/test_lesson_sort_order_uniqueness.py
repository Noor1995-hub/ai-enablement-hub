"""`UNIQUE (module_id, sort_order)` on lessons (review finding 6.5) is
DEFERRABLE INITIALLY DEFERRED, so it is invisible to the integration
harness's per-test savepoint rollback unless a test forces the check:
Postgres never re-validates a deferred constraint until COMMIT (which this
harness never reaches, by design) or an explicit
`SET CONSTRAINTS ... IMMEDIATE`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text, update
from sqlalchemy.exc import IntegrityError

from src.db.models import Lesson
from src.repositories.content_repository import ContentRepository
from tests.fixtures.factories import create_lesson, create_module, create_track

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_CHECK_IMMEDIATE = text("SET CONSTRAINTS uq_lessons_module_id_sort_order IMMEDIATE")


async def test_duplicate_sort_order_raises_once_checked_immediate(
    db_session: AsyncSession,
) -> None:
    track = await create_track(db_session, "Sort Order Track")
    module = await create_module(db_session, track, "Sort Order Module")
    lesson_a = await create_lesson(db_session, module, "A", sort_order=0)
    lesson_b = await create_lesson(db_session, module, "B", sort_order=1)

    # Deferred: writing a duplicate is not caught at statement time.
    await db_session.execute(
        update(Lesson).where(Lesson.id == lesson_b.id).values(sort_order=lesson_a.sort_order)
    )

    with pytest.raises(IntegrityError):
        await db_session.execute(_CHECK_IMMEDIATE)
    await db_session.rollback()


async def test_reorder_permutation_succeeds_while_deferred(db_session: AsyncSession) -> None:
    track = await create_track(db_session, "Sort Order Track 2")
    module = await create_module(db_session, track, "Sort Order Module 2")
    lesson_a = await create_lesson(db_session, module, "A", sort_order=0)
    lesson_b = await create_lesson(db_session, module, "B", sort_order=1)

    repo = ContentRepository(db_session)
    # A straight swap, applied lesson-by-lesson (set_lesson_orders issues one
    # UPDATE per lesson): setting lesson_a's sort_order to 1 first passes
    # through an intermediate state where both rows read sort_order=1. Only
    # safe because the constraint is deferred — this is exactly the case the
    # migration's docstring calls out.
    await repo.set_lesson_orders([(lesson_a.id, 1), (lesson_b.id, 0)])

    # Prove the final state is actually consistent, not merely "not yet
    # checked": force the deferred check now that the swap is complete.
    await db_session.execute(_CHECK_IMMEDIATE)

    lessons = await repo.list_lessons(module.id)
    assert {lesson.id: lesson.sort_order for lesson in lessons} == {
        lesson_a.id: 1,
        lesson_b.id: 0,
    }
