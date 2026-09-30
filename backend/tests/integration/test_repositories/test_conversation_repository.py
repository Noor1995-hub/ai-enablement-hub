# backend/tests/integration/test_repositories/test_conversation_repository.py
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import update

from src.db.models import Conversation
from src.repositories.conversation_repository import ConversationRepository
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_create_and_get_by_id(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="convo-repo@example.com")
    repo = ConversationRepository(db_session)

    created = await repo.create(user_id=user.id, kind="chatbot")
    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.user_id == user.id
    assert fetched.kind == "chatbot"


async def test_list_for_user_filters_by_kind(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="convo-repo-2@example.com")
    repo = ConversationRepository(db_session)
    await repo.create(user_id=user.id, kind="chatbot")
    await repo.create(user_id=user.id, kind="lesson")

    chatbot_only = await repo.list_for_user(user.id, "chatbot")

    assert len(chatbot_only) == 1
    assert chatbot_only[0].kind == "chatbot"


async def test_list_for_user_limit_caps_at_newest(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="convo-repo-4@example.com")
    repo = ConversationRepository(db_session)
    first = await repo.create(user_id=user.id, kind="chatbot")
    second = await repo.create(user_id=user.id, kind="chatbot")
    third = await repo.create(user_id=user.id, kind="chatbot")
    # now() is constant inside the test transaction, so pin distinct timestamps.
    t0 = datetime.now(UTC)
    for offset, convo in enumerate((first, second, third)):
        await db_session.execute(
            update(Conversation)
            .where(Conversation.id == convo.id)
            .values(updated_at=t0 + timedelta(seconds=offset))
        )
    await db_session.commit()

    capped = await repo.list_for_user(user.id, "chatbot", limit=2)
    uncapped = await repo.list_for_user(user.id, "chatbot", limit=None)

    assert [c.id for c in capped] == [third.id, second.id]
    assert [c.id for c in uncapped] == [third.id, second.id, first.id]


async def test_list_for_user_breaks_updated_at_ties_by_id_desc(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="convo-repo-5@example.com")
    repo = ConversationRepository(db_session)
    rows = [await repo.create(user_id=user.id, kind="chatbot") for _ in range(5)]
    tie_time = datetime.now(UTC)
    await db_session.execute(
        update(Conversation)
        .where(Conversation.id.in_([c.id for c in rows]))
        .values(updated_at=tie_time)
    )
    await db_session.commit()

    result = await repo.list_for_user(user.id, "chatbot")

    assert [c.id for c in result] == sorted((c.id for c in rows), reverse=True)


async def test_touch_updates_updated_at(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="convo-repo-3@example.com")
    repo = ConversationRepository(db_session)
    created = await repo.create(user_id=user.id, kind="chatbot")
    original = created.updated_at

    await repo.touch(created.id)
    refreshed = await repo.get_by_id(created.id)

    assert refreshed is not None
    assert refreshed.updated_at >= original
