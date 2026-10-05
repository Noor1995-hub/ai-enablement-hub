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
from src.services.exceptions import AiGenerationError, ConflictError, DomainError, NotFoundError
from src.services.interview_language import (
    DEFAULT_LANGUAGE,
    InterviewLanguage,
    language_directive,
    resolve_language,
)
from src.services.interview_marker import has_ready_marker, strip_ready_marker
from src.services.llm_service import (
    THINKING_MODE,
    is_provider_error,
    is_transient_provider_error,
)
from src.services.playbook_document import (
    PlaybookFormatError,
    output_template,
    parse_playbook,
)
from src.services.playbook_guardrails import drop_unnamed_systems
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
# A ceiling, not a target: playbooks are typically ~6k tokens in English and ~7k in Dutch,
# and long Dutch interviews ran into 8192 and failed twice (eval v9, #83). 12288 still
# fits a full generation inside _GENERATION_TIMEOUT_SECONDS.
_MAX_TOKENS = 12288
_GENERATE_PROMPT = "Write the playbook now, in the template under Output."
# How the model writes the playbook (#149): a tagged document parsed by code, not JSON in
# a tool call. Stored in the run metadata.
_PLAYBOOK_FORMAT = "tagged-v1"
_OPENER_MAX_TOKENS = 1024
_KICKOFF = "[Begin the interview now: greet me and ask your first question.]"

# The opener is one short streamed greeting; bound it well inside the 240 s ingress
# timeout so a hung provider call answers the learner instead of the ingress doing it.
_OPENER_TIMEOUT_SECONDS = 45.0
# One budget for the whole generation (both attempts, and the SDK's own retries inside
# them). Azure Container Apps ends every HTTP request at 240 s and our plan can't change
# that, so the build gets as much of it as is safe: 15 s stay for saving and responding,
# and the learner gets our "try again" message, not a dropped connection. A longer build
# needs it to run in the background instead (#149 follow-up).
_GENERATION_TIMEOUT_SECONDS = 225.0
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


# A provider failure is the provider's problem, not the request's: AiGenerationError (502).
# A transient one gets "try again" wording, anything else a neutral "failed".
_BUSY_MESSAGE = "The AI service is busy right now - please try again in a minute."


def _provider_failure(exc: BaseException, fallback: str) -> AiGenerationError:
    return AiGenerationError(_BUSY_MESSAGE if is_transient_provider_error(exc) else fallback)


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
    if isinstance(exc, PlaybookFormatError):
        return "; ".join(exc.problems)
    return f"{type(exc).__name__}: {exc}"


class _CutOffError(Exception):
    """The playbook stream stopped at max_tokens: what arrived is incomplete."""


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
        language = resolve_language(conversation.language)
        if conversation.summary is None:
            return InterviewStateResponse(
                status="in_progress", conversation_id=conversation.id, language=language
            )
        return InterviewStateResponse(
            status="complete",
            conversation_id=conversation.id,
            playbook=PlaybookShared.model_validate(conversation.summary["shared"]),
            language=language,
        )

    async def status_for(self, *, user: User) -> Literal["not_started", "in_progress", "complete"]:
        """The journey-pill status, derived from the same source as get_state
        but without materialising the playbook."""
        conversation = await self._interview_conversation(user.id)
        if conversation is None:
            return "not_started"
        return "in_progress" if conversation.summary is None else "complete"

    async def open_interview(
        self, *, user: User, language: InterviewLanguage = DEFAULT_LANGUAGE
    ) -> InterviewOpenerResponse:
        """Generate the AI's opening greeting for a fresh interview. Idempotent:
        if a conversation already exists, return its first assistant message
        (no LLM call, no new conversation). Otherwise generate the greeting from
        a synthetic, non-persisted kickoff user turn and persist only the
        assistant turn, so the stored transcript starts with the assistant.
        `language` is the learner's pick (#83): chosen once, so an existing
        conversation keeps its own."""
        existing = await self._interview_conversation(user.id)
        if existing is not None:
            rows = await self._messages.list_for_conversation(existing.id)
            greeting = next((m.content for m in rows if m.role == "assistant"), "")
            return InterviewOpenerResponse(
                conversation_id=existing.id,
                greeting=greeting,
                language=resolve_language(existing.language),
            )

        system = (
            f"{load_prompt(_KIND)}\n\n{await self._context.build_briefing(user)}"
            f"\n\n{language_directive(language)}"
        )
        try:
            chunks: list[str] = []
            async with (
                asyncio.timeout(_OPENER_TIMEOUT_SECONDS),
                self._llm.stream_reply(
                    system=system,
                    messages=[{"role": "user", "content": _KICKOFF}],
                    max_tokens=_OPENER_MAX_TOKENS,
                ) as reply,
            ):
                async for text in reply:
                    chunks.append(text)
            greeting = "".join(chunks).strip()
        except Exception as exc:  # noqa: BLE001 - re-raised unless a timeout or provider failure
            logger.warning("interview opener failed for user %s", user.id, exc_info=exc)
            # Same line as _generate: the provider failing (or taking too long) is a 502 the
            # UI offers a retry for; anything else is a bug and propagates as a 500.
            if not (isinstance(exc, TimeoutError) or is_provider_error(exc)):
                raise
            raise _provider_failure(
                exc, "Could not start the interview - please try again."
            ) from exc
        if not greeting:
            logger.warning("interview opener failed for user %s: empty greeting", user.id)
            raise DomainError("Could not start the interview - please try again.")

        conversation = await self._conversations.create_interview_if_absent(
            user.id, language=language
        )
        if conversation is None:
            # Lost the race to a concurrent opener (partial unique index
            # uq_conversations_interview_user_id): return the winner's conversation
            # and drop our greeting. The winner inserts its greeting only after the
            # conversation, so it may not exist yet: the greeting is then "" and the
            # page re-reads it via GET /api/interview/me.
            winner = await self._interview_conversation(user.id)
            if winner is None:  # the winner was reset in between: let the caller retry
                raise ConflictError("Could not start the interview - please try again.")
            rows = await self._messages.list_for_conversation(winner.id)
            greeting = next((m.content for m in rows if m.role == "assistant"), "")
            return InterviewOpenerResponse(
                conversation_id=winner.id,
                greeting=greeting,
                language=resolve_language(winner.language),
            )
        await self._messages.create(
            conversation.id,
            role="assistant",
            content=greeting,
            metadata={"model": self._llm.model, "prompt_version": prompt_version(_KIND)},
        )
        await self._conversations.touch(conversation.id)
        return InterviewOpenerResponse(
            conversation_id=conversation.id, greeting=greeting, language=language
        )

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
            .replace("{output_template}", output_template())
        ) + f"\n\n{language_directive(conversation.language)}"

        extraction, usage, attempts = await self._generate(system, conversation_id=conversation.id)
        # The person's own words: what a system in the shared box must come from (#149).
        sources = [m.content for m in rows if m.role == "user"] + [assessment]
        data, systems_dropped = drop_unnamed_systems(extraction.model_dump(mode="json"), sources)
        if systems_dropped:
            logger.info(
                "playbook for conversation %s: dropped %d system(s) the person never named",
                conversation.id,
                systems_dropped,
            )
        summary = cast("dict[str, Any]", _sanitize_dashes(data))
        summary["meta"] = self._run_meta(
            usage=usage, attempts=attempts, systems_dropped=systems_dropped
        )
        await self._conversations.update_summary(conversation.id, summary)
        return PlaybookShared.model_validate(summary["shared"])

    async def _generate(
        self, system: str, *, conversation_id: uuid.UUID
    ) -> tuple[PlaybookExtraction, LlmUsage, int]:
        """Two attempts inside one time budget. Returns the extraction, the usage of the call
        that produced it, and which attempt (1 or 2) that was.

        The model writes the playbook as a tagged document (#149) and code parses it, so the
        person's quotes need no JSON escaping. A cut-off stream, a document that doesn't match
        the template, or one that fails the schema is unusable and retried once. A timeout or
        a provider failure is not: the SDK has already retried those itself, so another round
        only burns the budget. Both are a 502 (AiGenerationError). Anything else is a bug and
        propagates as a 500."""
        last_error: Exception | None = None
        try:
            async with asyncio.timeout(_GENERATION_TIMEOUT_SECONDS):
                for attempt in (1, 2):
                    try:
                        text, usage = await self._stream_document(system)
                        if usage.stop_reason == "max_tokens":
                            raise _CutOffError("cut off at max_tokens")
                        extraction = PlaybookExtraction.model_validate(parse_playbook(text))
                        return extraction, usage, attempt
                    except (ValidationError, PlaybookFormatError, _CutOffError) as exc:
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
            raise AiGenerationError(
                "Building your playbook took too long - please try again."
            ) from exc
        except Exception as exc:  # noqa: BLE001 - re-raised unless a provider failure
            if not is_provider_error(exc):
                raise
            if is_transient_provider_error(exc):
                logger.warning(
                    "playbook generation: provider unavailable (%s) (conversation %s)",
                    type(exc).__name__,
                    conversation_id,
                )
            else:
                logger.error(
                    "playbook generation: provider call failed (%s) (conversation %s)",
                    type(exc).__name__,
                    conversation_id,
                )
            raise _provider_failure(
                exc, "Could not generate the playbook - please try again."
            ) from exc
        logger.error(
            "playbook generation failed after 2 attempts (conversation %s): %s",
            conversation_id,
            _describe_generation_error(last_error) if last_error is not None else "unknown",
        )
        raise DomainError("Could not generate the playbook - please try again.") from last_error

    async def _stream_document(self, system: str) -> tuple[str, LlmUsage]:
        chunks: list[str] = []
        async with self._llm.stream_reply(
            system=system,
            messages=[{"role": "user", "content": _GENERATE_PROMPT}],
            max_tokens=_MAX_TOKENS,
        ) as reply:
            async for chunk in reply:
                chunks.append(chunk)
            usage = await reply.usage()
        return "".join(chunks), usage

    def _run_meta(self, *, usage: LlmUsage, attempts: int, systems_dropped: int) -> dict[str, Any]:
        """Which prompts, model and settings produced this playbook (spec 2026-09-26 A.1).
        Stored next to the two boxes in conversations.summary. Nothing learner-facing
        reads it: get_state and get_admin_view only read "shared" and "internal"."""
        return {
            "model": self._llm.model,
            "prompt_version": prompt_version("interview_playbook"),
            "interview_prompt_version": prompt_version(_KIND),
            "max_tokens": _MAX_TOKENS,
            "thinking": THINKING_MODE,
            "format": _PLAYBOOK_FORMAT,
            "stop_reason": usage.stop_reason,
            "attempts": attempts,
            "systems_dropped": systems_dropped,
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

        language = resolve_language(conversation.language)
        if conversation.summary is None:
            return AdminInterviewResponse(
                status="in_progress", language=language, transcript=transcript
            )

        internal = PlaybookInternal.model_validate(conversation.summary["internal"])
        shared = PlaybookShared.model_validate(conversation.summary["shared"])
        return AdminInterviewResponse(
            status="complete",
            language=language,
            tier=internal.input_quality.tier,
            internal=internal,
            shared=shared,
            transcript=transcript,
        )

    async def reset(self, *, user_id: uuid.UUID) -> None:
        conversations = await self._conversations.list_for_user(user_id, _KIND)
        for conversation in conversations:
            await self._conversations.delete(conversation.id)
