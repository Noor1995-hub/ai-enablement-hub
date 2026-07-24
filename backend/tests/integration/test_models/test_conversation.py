# backend/tests/integration/test_models/test_conversation.py
from __future__ import annotations

from typing import TYPE_CHECKING

from src.db.models import Conversation, Message
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_conversation_and_message_round_trip(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="chat-model@example.com")

    conversation = Conversation(user_id=user.id, kind="chatbot")
    db_session.add(conversation)
    await db_session.flush()

    message = Message(conversation_id=conversation.id, role="user", content="hi")
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(conversation)
    await db_session.refresh(message)

    assert conversation.context_ref is None
    assert conversation.summary is None
    assert message.metadata_ is None
    assert message.role == "user"
