"""In-memory stand-ins for the real repositories and context services, so the eval can
drive InterviewService/ChatService over a frozen transcript with no database (spec §8).
Every fake constructs the same concrete src.db.models types the real repositories return,
so ty-src type-checks this the same way it would the production call sites."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from src.db.models import Conversation, Message
from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
from src.services.interview_context import TOOLS, InterviewContextService

__all__ = [
    "TOOLS",
    "InMemoryConversationRepository",
    "InMemoryMessageRepository",
    "StubLearningService",
    "StubMaturityService",
    "StubSurveyService",
    "build_context",
]


class InMemoryConversationRepository(AbstractConversationRepository):
    """One process-lifetime dict of conversations. No AsyncSession: the eval never opens
    one (spec §8)."""

    def __init__(self) -> None:
        self._rows: dict[uuid.UUID, Conversation] = {}

    def seed(self, *, user_id: uuid.UUID, kind: str) -> Conversation:
        now = datetime.now(UTC)
        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=user_id,
            kind=kind,
            context_ref=None,
            summary=None,
            created_at=now,
            updated_at=now,
        )
        self._rows[conversation.id] = conversation
        return conversation

    async def create(
        self, *, user_id: uuid.UUID, kind: str, context_ref: str | None = None
    ) -> Conversation:
        return self.seed(user_id=user_id, kind=kind)

    async def create_interview_if_absent(self, user_id: uuid.UUID) -> Conversation | None:
        if await self.list_for_user(user_id, "interview"):
            return None
        return self.seed(user_id=user_id, kind="interview")

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        return self._rows.get(conversation_id)

    async def list_for_user(
        self, user_id: uuid.UUID, kind: str, *, limit: int | None = None
    ) -> list[Conversation]:
        matches = [c for c in self._rows.values() if c.user_id == user_id and c.kind == kind]
        matches.sort(key=lambda c: (c.updated_at, c.id), reverse=True)
        return matches[:limit] if limit is not None else matches

    async def touch(self, conversation_id: uuid.UUID) -> None:
        pass  # nothing in the eval reads updated_at

    async def update_summary(self, conversation_id: uuid.UUID, summary: dict[str, Any]) -> None:
        self._rows[conversation_id].summary = summary

    async def delete(self, conversation_id: uuid.UUID) -> None:
        self._rows.pop(conversation_id, None)


class InMemoryMessageRepository(AbstractMessageRepository):
    def __init__(self) -> None:
        self._rows: dict[uuid.UUID, list[Message]] = {}

    def seed(self, conversation_id: uuid.UUID, turns: list[dict[str, str]]) -> None:
        """turns: the case's frozen transcript, e.g. [{"role": "assistant", "content": "..."}]."""
        now = datetime.now(UTC)
        self._rows[conversation_id] = [
            Message(
                id=uuid.uuid4(),
                conversation_id=conversation_id,
                role=t["role"],
                content=t["content"],
                metadata_=None,
                created_at=now,
            )
            for t in turns
        ]

    async def create(
        self,
        conversation_id: uuid.UUID,
        *,
        role: str,
        content: str,
        metadata: dict[str, Any] | None,
    ) -> Message:
        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_=metadata,
            created_at=datetime.now(UTC),
        )
        self._rows.setdefault(conversation_id, []).append(message)
        return message

    async def list_for_conversation(self, conversation_id: uuid.UUID) -> list[Message]:
        return list(self._rows.get(conversation_id, []))

    async def list_recent(self, conversation_id: uuid.UUID, *, limit: int) -> list[Message]:
        return list(self._rows.get(conversation_id, []))[-limit:]


class StubSurveyService:
    """Returns one fixed survey-shaped object for every user: the case's own assessment.
    InterviewContextService only reads attributes off it, so this need not be a real
    SurveyService (which needs a database)."""

    def __init__(self, survey: object) -> None:
        self._survey = survey

    async def get_own(self, user_id: uuid.UUID) -> object:
        return self._survey


class StubMaturityService:
    def __init__(self, level: str | None) -> None:
        self._level = level

    async def effective_level(self, user: object) -> str | None:
        return self._level


class StubLearningService:
    def __init__(self, status: str = "not_started") -> None:
        self._status = status

    async def learning_status(self, user_id: uuid.UUID) -> str:
        return self._status


def build_context(case: dict[str, Any]) -> InterviewContextService:
    """A real InterviewContextService, driven off the case's own `assessment` block
    instead of a database (spec §4.2: "over stub survey/maturity/learning services that
    return the case's assessment"). Field names mirror src/db/models/survey.py exactly,
    so InterviewContextService's attribute reads work unchanged."""
    a = case["assessment"]
    survey = type(
        "FixedSurvey",
        (),
        {
            "job_title": a.get("job_title"),
            "department": a.get("department"),
            "b_freq": a.get("b_freq"),
            "b_tools": a.get("b_tools"),
            "b_setup": a.get("b_setup"),
            "b_barriers": a.get("b_barriers"),
            "q_timesink": a.get("q_timesink"),
            "q_excitement": a.get("q_excitement"),
            "score_level": a.get("score_level"),
            "usage_band": a.get("usage_band"),
            "c1_code": a.get("c1_code"),
            "c2_code": a.get("c2_code"),
            "c3_code": a.get("c3_code"),
            "c4_code": a.get("c4_code"),
            "c5_codes": a.get("c5_codes"),
            "c6_code": a.get("c6_code"),
        },
    )()
    return InterviewContextService(
        StubSurveyService(survey),  # ty: ignore[invalid-argument-type]
        StubMaturityService(a.get("effective_level")),  # ty: ignore[invalid-argument-type]
        StubLearningService(a.get("learning_status", "not_started")),  # ty: ignore[invalid-argument-type]
    )
