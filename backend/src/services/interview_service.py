from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import ValidationError

from src.schemas.interview import (
    AdminInterviewResponse,
    InterviewOpenerResponse,
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
_OPENER_MAX_TOKENS = 1024
_KICKOFF = "[Begin the interview now: greet me and ask your first question.]"

# The interviewer appends this marker to the turn where it offers to build the playbook
# (prompts/interview.md) — a UI signal the frontend detects to reveal the build button.
# It's not conversation, so strip it from both the generation transcript and the admin view.
_READY_MARKER = "[[READY_TO_BUILD]]"


def _strip_ready_marker(text: str) -> str:
    return text.replace(_READY_MARKER, "").rstrip() if _READY_MARKER in text else text


# Belt-and-suspenders to the prompt's no-dash rule: the model still occasionally
# emits em/en dashes. Normalise them to a plain hyphen in generated playbook
# content (both boxes) before persisting/returning. Recurses str/list/dict.
_DASH_CHARS = ("—", "–", "―")  # em dash, en dash, horizontal bar


def _sanitize_dashes(value: object) -> object:
    if isinstance(value, str):
        for ch in _DASH_CHARS:
            value = value.replace(ch, "-")
        return value
    if isinstance(value, list):
        return [_sanitize_dashes(v) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_dashes(v) for k, v in value.items()}
    return value


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

    async def status_for(self, *, user: User) -> Literal["not_started", "in_progress", "complete"]:
        """The journey-pill status, derived from the same source as get_state
        but without materialising the playbook."""
        conversation = await self._interview_conversation(user.id)
        if conversation is None:
            return "not_started"
        return "in_progress" if conversation.summary is None else "complete"

    async def open_interview(self, *, user: User) -> InterviewOpenerResponse:
        """Generate the AI's opening greeting for a fresh interview. Idempotent:
        if a conversation already exists, return its first assistant message
        (no LLM call, no new conversation). Otherwise generate the greeting from
        a synthetic, non-persisted kickoff user turn and persist only the
        assistant turn, so the stored transcript starts with the assistant."""
        existing = await self._interview_conversation(user.id)
        if existing is not None:
            rows = await self._messages.list_for_conversation(existing.id)
            greeting = next((m.content for m in rows if m.role == "assistant"), "")
            return InterviewOpenerResponse(conversation_id=existing.id, greeting=greeting)

        system = f"{load_prompt(_KIND)}\n\n{await self._context.build_briefing(user)}"
        try:
            chunks: list[str] = []
            async with self._llm.stream_reply(
                system=system,
                messages=[{"role": "user", "content": _KICKOFF}],
                max_tokens=_OPENER_MAX_TOKENS,
            ) as reply:
                async for text in reply:
                    chunks.append(text)
            greeting = "".join(chunks).strip()
        except Exception as exc:  # noqa: BLE001 - best-effort opener; the UI offers retry
            raise DomainError("Could not start the interview - please try again.") from exc
        if not greeting:
            raise DomainError("Could not start the interview - please try again.")

        conversation = await self._conversations.create(user_id=user.id, kind=_KIND)
        await self._messages.create(
            conversation.id, role="assistant", content=greeting, metadata=None
        )
        await self._conversations.touch(conversation.id)
        return InterviewOpenerResponse(conversation_id=conversation.id, greeting=greeting)

    async def build_playbook(self, *, user: User) -> PlaybookShared:
        conversation = await self._interview_conversation(user.id)
        if conversation is None:
            raise NotFoundError("Interview")
        if conversation.summary is not None:
            return PlaybookShared.model_validate(conversation.summary["shared"])

        rows = await self._messages.list_for_conversation(conversation.id)
        transcript = "\n".join(f"{m.role}: {_strip_ready_marker(m.content)}" for m in rows)
        assessment = await self._context.build_assessment_context(user)
        system = (
            load_prompt("interview_playbook")
            .replace("{first_name}", user.first_name)
            .replace("{assessment_json}", assessment)
            .replace("{company_context}", "")
            .replace("{transcript}", transcript)
        )

        extraction = await self._generate(system)
        summary = cast("dict[str, Any]", _sanitize_dashes(extraction.model_dump(mode="json")))
        await self._conversations.update_summary(conversation.id, summary)
        return PlaybookShared.model_validate(summary["shared"])

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
        transcript = [
            TranscriptMessage(role=m.role, content=_strip_ready_marker(m.content)) for m in rows
        ]

        if conversation.summary is None:
            return AdminInterviewResponse(status="in_progress", transcript=transcript)

        internal = PlaybookInternal.model_validate(conversation.summary["internal"])
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
