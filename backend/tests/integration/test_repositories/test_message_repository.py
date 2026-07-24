# backend/tests/integration/test_repositories/test_message_repository.py
from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.conversation_repository import ConversationRepository
from src.repositories.message_repository import MessageRepository
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_create_and_list_for_conversation(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="msg-repo@example.com")
    conversations = ConversationRepository(db_session)
    messages = MessageRepository(db_session)
    conversation = await conversations.create(user_id=user.id, kind="chatbot")

    await messages.create(conversation.id, role="user", content="hi", metadata=None)
    await messages.create(
        conversation.id, role="assistant", content="hello!", metadata={"truncated": False}
    )

    rows = await messages.list_for_conversation(conversation.id)

    assert [m.role for m in rows] == ["user", "assistant"]
    assert rows[1].metadata_ == {"truncated": False}


async def test_list_recent_returns_last_n_in_chronological_order(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="msg-repo-2@example.com")
    conversations = ConversationRepository(db_session)
    messages = MessageRepository(db_session)
    conversation = await conversations.create(user_id=user.id, kind="chatbot")
    for i in range(5):
        await messages.create(conversation.id, role="user", content=f"msg {i}", metadata=None)

    recent = await messages.list_recent(conversation.id, limit=2)

    assert [m.content for m in recent] == ["msg 3", "msg 4"]
