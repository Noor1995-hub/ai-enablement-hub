from __future__ import annotations

import uuid
from types import SimpleNamespace

from evals.interviewer.fakes import (
    InMemoryConversationRepository,
    InMemoryMessageRepository,
    build_context,
)


async def test_conversation_repository_round_trips_a_seeded_conversation() -> None:
    conversations = InMemoryConversationRepository()
    user_id = uuid.uuid4()

    conversation = conversations.seed(user_id=user_id, kind="interview")

    found = await conversations.list_for_user(user_id, "interview")
    assert found == [conversation]
    assert conversation.summary is None


async def test_update_summary_persists_on_the_same_conversation() -> None:
    conversations = InMemoryConversationRepository()
    conversation = conversations.seed(user_id=uuid.uuid4(), kind="interview")

    await conversations.update_summary(conversation.id, {"shared": {}, "internal": {}, "meta": {}})

    reloaded = await conversations.get_by_id(conversation.id)
    assert reloaded is not None
    assert reloaded.summary == {"shared": {}, "internal": {}, "meta": {}}


async def test_delete_removes_the_conversation() -> None:
    conversations = InMemoryConversationRepository()
    conversation = conversations.seed(user_id=uuid.uuid4(), kind="interview")

    await conversations.delete(conversation.id)

    assert await conversations.get_by_id(conversation.id) is None


async def test_message_repository_seeds_and_lists_chronologically() -> None:
    messages = InMemoryMessageRepository()
    conversation_id = uuid.uuid4()

    messages.seed(
        conversation_id,
        [
            {"role": "assistant", "content": "Hi, what do you do?"},
            {"role": "user", "content": "I run the monthly close."},
        ],
    )

    rows = await messages.list_for_conversation(conversation_id)
    assert [r.role for r in rows] == ["assistant", "user"]
    assert rows[0].content == "Hi, what do you do?"
    assert await messages.list_recent(conversation_id, limit=1) == rows[-1:]


async def test_message_repository_create_appends_after_the_seeded_transcript() -> None:
    messages = InMemoryMessageRepository()
    conversation_id = uuid.uuid4()
    messages.seed(conversation_id, [{"role": "assistant", "content": "Hi"}])

    created = await messages.create(conversation_id, role="user", content="hello", metadata=None)

    rows = await messages.list_for_conversation(conversation_id)
    assert [r.content for r in rows] == ["Hi", "hello"]
    assert created.content == "hello"


async def test_build_context_feeds_the_case_assessment_into_the_briefing() -> None:
    case = {
        "assessment": {
            "job_title": "CFO",
            "department": "Finance",
            "b_freq": "WEEKLY",
            "b_tools": ["COPILOT"],
            "b_setup": ["NONE"],
            "b_barriers": ["NO_TIME"],
            "q_timesink": "the month end close",
            "q_excitement": "reporting automation",
            "score_level": "practitioner",
            "usage_band": "regular",
            "c1_code": "HAVE",
            "c2_code": "PARTIAL",
            "c3_code": "PARTIAL",
            "c4_code": "HAVE",
            "c5_codes": ["APPROVED_PASTE"],
            "c6_code": "HAVE",
            "effective_level": "practitioner",
            "learning_status": "not_started",
        }
    }
    user = SimpleNamespace(id=uuid.uuid4(), first_name="Lotte", last_name="Verbeke")

    context = build_context(case)
    briefing = await context.build_briefing(user)  # ty: ignore[invalid-argument-type]

    assert "CFO" in briefing
    assert "the month end close" in briefing


async def test_create_interview_if_absent_mirrors_the_one_interview_rule() -> None:
    conversations = InMemoryConversationRepository()
    user_id = uuid.uuid4()
    conversations.seed(user_id=user_id, kind="chatbot")

    first = await conversations.create_interview_if_absent(user_id)
    second = await conversations.create_interview_if_absent(user_id)

    assert first is not None
    assert first.kind == "interview"
    assert second is None
    assert await conversations.list_for_user(user_id, "interview") == [first]
