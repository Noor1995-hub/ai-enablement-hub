# backend/tests/integration/test_repositories/test_conversation_repository.py
from __future__ import annotations

from typing import TYPE_CHECKING

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


async def test_touch_updates_updated_at(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="convo-repo-3@example.com")
    repo = ConversationRepository(db_session)
    created = await repo.create(user_id=user.id, kind="chatbot")
    original = created.updated_at

    await repo.touch(created.id)
    refreshed = await repo.get_by_id(created.id)

    assert refreshed is not None
    assert refreshed.updated_at >= original
