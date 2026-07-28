from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from src.schemas.interview import (
    AdminInterviewResponse,
    InterviewStateResponse,
    PlaybookExtraction,
    PlaybookInternal,
    PlaybookShared,
    TranscriptMessage,
)
from src.services.exceptions import DomainError, NotFoundError
from src.services.interview_schema import PLAYBOOK_SCHEMA
from src.services.llm_service import LlmError
from src.services.prompts import load_prompt

if TYPE_CHECKING:
    import uuid

    from src.db.models import Conversation, User
    from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
    from src.services.interview_context import InterviewContextService
    from src.services.llm_service import LlmClient

__all__ = ["InterviewService"]

_KIND = "interview"
_MAX_TOKENS = 8192
_GENERATE_PROMPT = "Produce the playbook now by calling the record_playbook tool."


class InterviewService:
    """Owns the interviewer's wrap-up generation (retry-once structured LLM
    call against the two-box T2 schema), the caller's own interview state,
    the admin two-box view, and reset."""

    def __init__(
        self,
        conversations: AbstractConversationRepository,
        messages: AbstractMessageRepository,
        llm: LlmClient,
        context: InterviewContextService,
    ) -> None:
        self._conversations = conversations
        self._messages = messages
        self._llm = llm
        self._context = context

    async def _interview_conversation(self, user_id: uuid.UUID) -> Conversation | None:
        conversations = await self._conversations.list_for_user(user_id, _KIND)
        return conversations[0] if conversations else None

    async def get_state(self, *, user: User) -> InterviewStateResponse:
        conversation = await self._interview_conversation(user.id)
        if conversation is None:
            return InterviewStateResponse(status="not_started")
        if conversation.summary is None:
            return InterviewStateResponse(status="in_progress", conversation_id=conversation.id)
        return InterviewStateResponse(
            status="complete",
            conversation_id=conversation.id,
            playbook=PlaybookShared.model_validate(conversation.summary["shared"]),
        )

    async def build_playbook(self, *, user: User) -> PlaybookShared:
        conversation = await self._interview_conversation(user.id)
        if conversation is None:
            raise NotFoundError("Interview")
        if conversation.summary is not None:
            return PlaybookShared.model_validate(conversation.summary["shared"])

        rows = await self._messages.list_for_conversation(conversation.id)
        transcript = "\n".join(f"{m.role}: {m.content}" for m in rows)
        assessment = await self._context.build_assessment_context(user)
        system = (
            load_prompt("interview_playbook")
            .replace("{first_name}", user.first_name)
            .replace("{assessment_json}", assessment)
            .replace("{company_context}", "")
            .replace("{transcript}", transcript)
        )

        extraction = await self._generate(system)
        summary = extraction.model_dump(mode="json")
        await self._conversations.update_summary(conversation.id, summary)
        return extraction.shared

    async def _generate(self, system: str) -> PlaybookExtraction:
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                result, _usage = await self._llm.complete_structured(
                    system=system,
                    prompt=_GENERATE_PROMPT,
                    schema=PLAYBOOK_SCHEMA,
                    max_tokens=_MAX_TOKENS,
                )
                return PlaybookExtraction.model_validate(result)
            except (ValidationError, LlmError) as exc:
                last_error = exc
        raise DomainError("Could not generate the playbook — please try again.") from last_error

    async def get_admin_view(self, *, user_id: uuid.UUID) -> AdminInterviewResponse:
        conversation = await self._interview_conversation(user_id)
        if conversation is None:
            return AdminInterviewResponse(status="not_started", transcript=[])

        rows = await self._messages.list_for_conversation(conversation.id)
        transcript = [TranscriptMessage(role=m.role, content=m.content) for m in rows]

        if conversation.summary is None:
            return AdminInterviewResponse(status="in_progress", transcript=transcript)

        internal = PlaybookInternal(**conversation.summary["internal"])
        shared = PlaybookShared.model_validate(conversation.summary["shared"])
        return AdminInterviewResponse(
            status="complete",
            tier=internal.input_quality.tier,
            internal=internal,
            shared=shared,
            transcript=transcript,
        )

    async def reset(self, *, user_id: uuid.UUID) -> None:
        conversations = await self._conversations.list_for_user(user_id, _KIND)
        for conversation in conversations:
            await self._conversations.delete(conversation.id)
