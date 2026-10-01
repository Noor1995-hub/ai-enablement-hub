"""One interview conversation per user (review finding 6.5): the partial unique
index `uq_conversations_interview_user_id` on `conversations (user_id) WHERE
kind = 'interview'`, and the race-safe insert that relies on it.

The index is NOT deferrable, so a duplicate fails at flush time, inside the
harness's savepoint, with no `SET CONSTRAINTS` needed."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.db.models import Conversation
from src.repositories.conversation_repository import ConversationRepository
from tests.fixtures.factories import create_user

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


async def _interview_count(db_session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db_session.execute(
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.user_id == user_id, Conversation.kind == "interview")
    )
    return result.scalar_one()


async def test_a_user_cannot_have_two_interview_conversations(db_session: AsyncSession) -> None:
    """InterviewService treats "one interview per user" as an invariant
    (_interview_conversation takes conversations[0]); the DB must enforce it, or
    a concurrent double-open hides one learner's transcript forever."""
    user = await create_user(db_session, email="one-interview@example.com")
    conversations = ConversationRepository(db_session)
    await conversations.create(user_id=user.id, kind="interview")

    with pytest.raises(IntegrityError):
        await conversations.create(user_id=user.id, kind="interview")
    await db_session.rollback()


async def test_the_guard_is_partial_and_leaves_other_kinds_alone(
    db_session: AsyncSession,
) -> None:
    """Chat conversations are many-per-user by design — the index must be
    partial, not a blanket unique on user_id."""
    user = await create_user(db_session, email="many-chats@example.com")
    conversations = ConversationRepository(db_session)
    await conversations.create(user_id=user.id, kind="interview")

    first = await conversations.create(user_id=user.id, kind="chatbot")
    second = await conversations.create(user_id=user.id, kind="chatbot")

    assert first.id != second.id


async def test_two_users_can_each_have_an_interview(db_session: AsyncSession) -> None:
    conversations = ConversationRepository(db_session)
    one = await create_user(db_session, email="interview-a@example.com")
    two = await create_user(db_session, email="interview-b@example.com")

    await conversations.create(user_id=one.id, kind="interview")
    await conversations.create(user_id=two.id, kind="interview")


async def test_create_interview_if_absent_creates_the_first(db_session: AsyncSession) -> None:
    user = await create_user(db_session, email="interview-first@example.com")
    conversations = ConversationRepository(db_session)
    # A chat conversation is not an interview: it must not count as "present".
    await conversations.create(user_id=user.id, kind="chatbot")

    created = await conversations.create_interview_if_absent(user.id)

    assert created is not None
    assert created.user_id == user.id
    assert created.kind == "interview"
    assert await _interview_count(db_session, user.id) == 1


async def test_create_interview_if_absent_returns_none_for_the_loser(
    db_session: AsyncSession,
) -> None:
    """The second opener loses without an IntegrityError (ON CONFLICT DO
    NOTHING on the partial index), so the session stays usable and the caller
    can re-read the winner."""
    user = await create_user(db_session, email="interview-race@example.com")
    conversations = ConversationRepository(db_session)
    winner = await conversations.create_interview_if_absent(user.id)
    assert winner is not None

    loser = await conversations.create_interview_if_absent(user.id)

    assert loser is None
    assert await _interview_count(db_session, user.id) == 1
    remaining = await conversations.list_for_user(user.id, "interview")
    assert [c.id for c in remaining] == [winner.id]


async def test_create_interview_if_absent_stores_the_chosen_language(
    db_session: AsyncSession,
) -> None:
    user = await create_user(db_session, email="interview-lang@example.com")
    conversations = ConversationRepository(db_session)

    created = await conversations.create_interview_if_absent(user.id, language="nl")

    assert created is not None
    assert created.language == "nl"
