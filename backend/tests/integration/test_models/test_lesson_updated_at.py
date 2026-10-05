from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from src.db.models import Lesson, User
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_a_new_lesson_gets_updated_at_and_no_editor(db_session: AsyncSession) -> None:
    module = await create_module(db_session, await create_track(db_session))
    lesson = await create_lesson(db_session, module)
    assert lesson.updated_at is not None
    assert lesson.updated_by is None


async def test_deleting_the_editor_keeps_the_lesson(db_session: AsyncSession) -> None:
    module = await create_module(db_session, await create_track(db_session))
    lesson = await create_lesson(db_session, module)
    editor = await create_user(db_session, email="b5-editor@example.com", role="admin")
    lesson.updated_by = editor.id
    await db_session.commit()

    await db_session.execute(delete(User).where(User.id == editor.id))
    await db_session.commit()

    refreshed = (
        await db_session.execute(select(Lesson).where(Lesson.id == lesson.id))
    ).scalar_one()
    await db_session.refresh(refreshed)
    assert refreshed.updated_by is None
