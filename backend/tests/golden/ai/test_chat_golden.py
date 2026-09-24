"""Golden cases for the three ChatService-driven surfaces: chatbot, assessment, lesson.

Fixtures are fictional and fully deterministic (fixed UUIDs, no wall-clock reads) so the
snapshot never drifts for reasons unrelated to a real prompt/history change.

Note on "lesson": the brief this test implements anticipated the lesson surface injecting
lesson content as a `system_suffix`. As built today, `routers/chat.py::_prepare_chat_message`
only ever passes a `system_suffix` for kind == "interview" (the assessment briefing) — the
frontend's `useChat`/`ChatPanel` never sends lesson content anywhere, and `prompts/lesson.md`
is still the Batch-A placeholder ("the real lesson-helper prompt ... is written in a later
batch"). So there is no lesson-context injection to reproduce yet: this test drives the same
real ChatService.send_message code path as chatbot/assessment (kind="lesson", no
system_suffix), which is the actual reachable behaviour today. Revisit once lesson context
injection ships.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
from src.services.chat_service import ChatService
from tests.golden.ai.harness import RecordingLlm, assert_golden, render_calls

_CONVERSATION_ID = uuid.UUID(int=10)
_USER_ID = uuid.UUID(int=11)


def _conversation(kind: str) -> SimpleNamespace:
    return SimpleNamespace(id=_CONVERSATION_ID, user_id=_USER_ID, kind=kind)


def _repos(*, prior_reply: str, new_user_message: str) -> tuple[AsyncMock, AsyncMock]:
    """A fixed fictional history: one prior assistant turn, then the new user turn
    (as the real repository would return once the user's turn is persisted)."""
    conversations = AsyncMock(spec=AbstractConversationRepository)
    messages = AsyncMock(spec=AbstractMessageRepository)
    messages.list_recent.return_value = [
        SimpleNamespace(role="assistant", content=prior_reply),
        SimpleNamespace(role="user", content=new_user_message),
    ]
    return conversations, messages


async def _send(kind: str, *, prior_reply: str, new_user_message: str, llm: RecordingLlm) -> None:
    conversations, messages = _repos(prior_reply=prior_reply, new_user_message=new_user_message)
    service = ChatService(conversations, messages, llm)  # ty: ignore[invalid-argument-type]
    conversation = _conversation(kind)
    async for _event in service.send_message(
        conversation=conversation,  # ty: ignore[invalid-argument-type]
        content=new_user_message,
    ):
        pass


async def test_chatbot_golden() -> None:
    llm = RecordingLlm(chunks=["ok"])
    await _send(
        "chatbot",
        prior_reply="Sure — what would you like help with today?",
        new_user_message="What's a good first AI use case for someone doing vendor invoice "
        "reconciliation at a fictional bakery company?",
        llm=llm,
    )

    assert_golden("chatbot", llm.calls)

    # determinism: a second identical run renders identically
    llm2 = RecordingLlm(chunks=["ok"])
    await _send(
        "chatbot",
        prior_reply="Sure — what would you like help with today?",
        new_user_message="What's a good first AI use case for someone doing vendor invoice "
        "reconciliation at a fictional bakery company?",
        llm=llm2,
    )
    assert render_calls(llm.calls) == render_calls(llm2.calls)


async def test_assessment_golden() -> None:
    llm = RecordingLlm(chunks=["ok"])
    await _send(
        "assessment",
        prior_reply="Tell me a bit more about how often you use AI tools day to day.",
        new_user_message="A few times a week, mostly to draft emails and summarise meeting notes.",
        llm=llm,
    )

    assert_golden("assessment", llm.calls)

    llm2 = RecordingLlm(chunks=["ok"])
    await _send(
        "assessment",
        prior_reply="Tell me a bit more about how often you use AI tools day to day.",
        new_user_message="A few times a week, mostly to draft emails and summarise meeting notes.",
        llm=llm2,
    )
    assert render_calls(llm.calls) == render_calls(llm2.calls)


async def test_lesson_golden() -> None:
    llm = RecordingLlm(chunks=["ok"])
    await _send(
        "lesson",
        prior_reply="Happy to help with this lesson — what's unclear?",
        new_user_message="In the 'Prompting basics' lesson, what does it mean to be specific "
        "in a prompt?",
        llm=llm,
    )

    assert_golden("lesson", llm.calls)

    llm2 = RecordingLlm(chunks=["ok"])
    await _send(
        "lesson",
        prior_reply="Happy to help with this lesson — what's unclear?",
        new_user_message="In the 'Prompting basics' lesson, what does it mean to be specific "
        "in a prompt?",
        llm=llm2,
    )
    assert render_calls(llm.calls) == render_calls(llm2.calls)
