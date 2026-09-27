from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
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
from src.services.exceptions import ConflictError, DomainError, NotFoundError
from src.services.interview_marker import has_ready_marker, strip_ready_marker
from src.services.interview_schema import PLAYBOOK_SCHEMA
from src.services.llm_service import THINKING_MODE, LlmError, is_transient_provider_error
from src.services.prompts import load_prompt, prompt_version

if TYPE_CHECKING:
    import uuid

    from src.db.models import Conversation, Message, User
    from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
    from src.services.interview_context import InterviewContextService
    from src.services.llm_service import LlmClient, LlmUsage

logger = logging.getLogger(__name__)

__all__ = ["InterviewService"]

_KIND = "interview"
_MAX_TOKENS = 8192
_GENERATE_PROMPT = "Produce the playbook now by calling the record_playbook tool."
_OPENER_MAX_TOKENS = 1024
_KICKOFF = "[Begin the interview now: greet me and ask your first question.]"

# One budget for the whole generation (both attempts, and the SDK's own retries inside
# them). Sized under the Container Apps ingress timeout of 240 s, same reasoning as
# content_improvement_service._PER_LESSON_TIMEOUT_SECONDS.
_GENERATION_TIMEOUT_SECONDS = 180.0
# Chat messages have no length limit, so the transcript is unbounded. ~25k tokens is far
# past any real interview (the longest in production so far is ~20 answers, ~12k chars).
# Refuse rather than truncate: half a transcript makes a confidently wrong playbook.
_MAX_TRANSCRIPT_CHARS = 100_000

# Belt-and-suspenders to the prompt's no-dash rule: the model still occasionally
# emits em/en dashes. Normalise them to a plain hyphen in generated playbook
# content (both boxes) before persisting/returning. Recurses str/list/dict.
_DASH_CHARS = ("—", "–", "―")  # em dash, en dash, horizontal bar

# Server-side twin of the Build button rule in frontend/src/pages/Interview.tsx
# (`canBuild = modelReady || answerCount >= FALLBACK_MIN_ANSWERS`). Keep the two numbers equal.
_MIN_ANSWERS_WITHOUT_OFFER = 6


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


def _describe_generation_error(exc: Exception) -> str:
    """Loggable summary of an unusable generation: error locations and types only, never
    the model output (it is derived from the learner's interview)."""
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['type']}"
            for e in exc.errors(include_url=False, include_input=False)
        )
    return f"{type(exc).__name__}: {exc}"


def _ensure_ready(rows: Sequence[Message]) -> None:
    """Refuse to build before the interviewer offered to, unless the learner has given
    enough answers for the manual fallback. Only an assistant turn counts as the offer:
    a learner typing the marker proves nothing."""
    offered = any(m.role == "assistant" and has_ready_marker(m.content) for m in rows)
    answers = sum(1 for m in rows if m.role == "user")
    if not offered and answers < _MIN_ANSWERS_WITHOUT_OFFER:
        raise ConflictError("Answer a few more questions before building your playbook.")


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
            logger.warning("interview opener failed for user %s", user.id, exc_info=exc)
            raise DomainError("Could not start the interview - please try again.") from exc
        if not greeting:
            logger.warning("interview opener failed for user %s: empty greeting", user.id)
            raise DomainError("Could not start the interview - please try again.")

        conversation = await self._conversations.create(user_id=user.id, kind=_KIND)
        await self._messages.create(
            conversation.id,
            role="assistant",
            content=greeting,
            metadata={"model": self._llm.model, "prompt_version": prompt_version(_KIND)},
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
        _ensure_ready(rows)
        transcript = "\n".join(f"{m.role}: {strip_ready_marker(m.content)}" for m in rows)
        if len(transcript) > _MAX_TRANSCRIPT_CHARS:
            logger.warning(
                "interview %s transcript too long for a playbook (%d chars)",
                conversation.id,
                len(transcript),
            )
            raise DomainError(
                "This interview is too long to turn into a playbook. "
                "Please ask your hub admin to reset it."
            )
        assessment = await self._context.build_assessment_context(user)
        system = (
            load_prompt("interview_playbook")
            .replace("{first_name}", user.first_name)
            .replace("{assessment_json}", assessment)
            .replace("{company_context}", "")
            .replace("{transcript}", transcript)
        )

        extraction, usage, attempts = await self._generate(system, conversation_id=conversation.id)
        summary = cast("dict[str, Any]", _sanitize_dashes(extraction.model_dump(mode="json")))
        summary["meta"] = self._run_meta(usage=usage, attempts=attempts)
        await self._conversations.update_summary(conversation.id, summary)
        return PlaybookShared.model_validate(summary["shared"])

    async def _generate(
        self, system: str, *, conversation_id: uuid.UUID
    ) -> tuple[PlaybookExtraction, LlmUsage, int]:
        """Two attempts against the schema inside one time budget. Returns the extraction,
        the usage of the call that produced it, and which attempt (1 or 2) that was.

        Unusable output (schema mismatch, no tool_use block) is retried once. A timeout or
        a provider outage is not: the SDK has already retried those itself, so another
        round only burns the budget. Anything else is a bug and propagates as a 500."""
        last_error: Exception | None = None
        try:
            async with asyncio.timeout(_GENERATION_TIMEOUT_SECONDS):
                for attempt in (1, 2):
                    try:
                        result, usage = await self._llm.complete_structured(
                            system=system,
                            prompt=_GENERATE_PROMPT,
                            schema=PLAYBOOK_SCHEMA,
                            max_tokens=_MAX_TOKENS,
                        )
                        return PlaybookExtraction.model_validate(result), usage, attempt
                    except (ValidationError, LlmError) as exc:
                        logger.warning(
                            "playbook attempt %d unusable (conversation %s): %s",
                            attempt,
                            conversation_id,
                            _describe_generation_error(exc),
                        )
                        last_error = exc
        except TimeoutError as exc:
            logger.warning(
                "playbook generation timed out after %ss (conversation %s)",
                _GENERATION_TIMEOUT_SECONDS,
                conversation_id,
            )
            raise DomainError("Building your playbook took too long - please try again.") from exc
        except Exception as exc:  # noqa: BLE001 - re-raised unless transient
            if not is_transient_provider_error(exc):
                raise
            logger.warning(
                "playbook generation: provider unavailable (%s) (conversation %s)",
                type(exc).__name__,
                conversation_id,
            )
            raise DomainError(
                "The AI service is busy right now - please try again in a minute."
            ) from exc
        logger.error(
            "playbook generation failed after 2 attempts (conversation %s): %s",
            conversation_id,
            _describe_generation_error(last_error) if last_error is not None else "unknown",
        )
        raise DomainError("Could not generate the playbook - please try again.") from last_error

    def _run_meta(self, *, usage: LlmUsage, attempts: int) -> dict[str, Any]:
        """Which prompts, model and settings produced this playbook (spec 2026-09-26 A.1).
        Stored next to the two boxes in conversations.summary. Nothing learner-facing
        reads it: get_state and get_admin_view only read "shared" and "internal"."""
        return {
            "model": self._llm.model,
            "prompt_version": prompt_version("interview_playbook"),
            "interview_prompt_version": prompt_version(_KIND),
            "max_tokens": _MAX_TOKENS,
            "thinking": THINKING_MODE,
            "attempts": attempts,
            "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens},
            "generated_at": datetime.now(UTC).isoformat(),
        }

    async def get_admin_view(self, *, user_id: uuid.UUID) -> AdminInterviewResponse:
        conversation = await self._interview_conversation(user_id)
        if conversation is None:
            return AdminInterviewResponse(status="not_started", transcript=[])

        rows = await self._messages.list_for_conversation(conversation.id)
        transcript = [
            TranscriptMessage(role=m.role, content=strip_ready_marker(m.content)) for m in rows
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
