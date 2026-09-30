"""InterviewService: wrap-up generation (retry-once structured LLM call),
state derivation, admin view, and reset. Pure-logic unit tests with mocked
repositories/services (AAA, no DB)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock

import anthropic
import pytest

from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
from src.schemas.interview import InterviewOpenerResponse, PlaybookInternal, PlaybookShared
from src.services import interview_service as interview_module
from src.services.exceptions import AiGenerationError, ConflictError, DomainError
from src.services.interview_context import InterviewContextService
from src.services.interview_service import InterviewService
from src.services.llm_service import LlmError, LlmUsage
from src.services.prompts import prompt_version
from tests.fixtures.llm import (
    FakeLlmClient,
    RaisingLlmClient,
    connection_error,
    overloaded_error,
    status_error,
)

# One fully-populated extraction: both boxes complete, one use_case
# (difficulty "Quick Win"), tier "RICH".
_EXTRACTION: dict[str, object] = {
    "internal": {
        "input_quality": {
            "tier": "RICH",
            "evidence": "Named systems and specific episodes throughout.",
            "what_to_probe_next": [],
        },
        "person": {
            "role_reality": "Runs monthly close single-handedly.",
            "influence": "Owns the process end to end.",
            "decision_rights": "Can adopt new tools without sign-off.",
            "champion_potential": "High — already evangelising internally.",
            "confidence": "high",
        },
        "pains": [
            {
                "pain": "Manual reconciliation across spreadsheets.",
                "evidence": "Described re-keying data from the ERP export every month.",
                "frequency": "monthly",
                "est_time_cost": "a full day",
                "basis": "stated",
                "confidence": "high",
            }
        ],
        "blockers": {
            "stated": ["no time to learn new tools"],
            "diagnosed": [
                {
                    "type": "time",
                    "reasoning": "Month-end leaves no slack for experimentation.",
                    "basis": "inferred from schedule description",
                    "confidence": "medium",
                }
            ],
        },
        "maturity": {
            "placement": "explorer",
            "behavioural_evidence": "Uses ChatGPT ad hoc, no saved prompts.",
            "vs_self_reported": "matches self-report",
            "trajectory": "ready to move to practitioner with structure",
        },
        "systems_landscape": [
            {
                "system": "NetSuite",
                "how_used": "Exports monthly reconciliation reports.",
                "implication": "Any automation must consume NetSuite exports.",
            }
        ],
        "company_context": "Mid-size finance team, inferred from role description.",
        "engagement_notes": {
            "opportunities": ["Champion for the finance track"],
            "risks": [],
            "follow_up_questions": ["What format are the NetSuite exports in?"],
        },
    },
    "shared": {
        "where_you_are_today": (
            "You've built a solid handle on the monthly close, and you're already reaching "
            "for AI tools when things get repetitive. The reconciliation work you described "
            "eats a full day every month, and that's exactly the kind of task worth automating "
            "first. You're not starting from zero here, you already know where the pain is."
        ),
        "use_cases": [
            {
                "rank": 1,
                "start_here": True,
                "name": "Automate the NetSuite reconciliation",
                "pain_it_kills": "the full day spent re-keying export data",
                "in_practice": "Upload the NetSuite export and let AI flag mismatches.",
                "before": "A full day of manual cross-checking.",
                "after": "An hour reviewing flagged exceptions.",
                "impact": "Most of a day back each month.",
                "difficulty": "Quick Win",
                "systems_involved": ["NetSuite"],
                "assumption_to_check": "That exports are consistently formatted month to month.",
                "cross_functional": False,
            }
        ],
        "next_moves": [
            {
                "order": 1,
                "move": "Try the reconciliation assistant on next month's export.",
                "why_now": "It directly targets the pain you described first.",
                "linked_use_case": 1,
            }
        ],
        "reframes": [
            {
                "their_hesitation": "I don't have time to learn a new tool.",
                "the_concern": "Learning curve costing more time than it saves.",
                "reframe": "Start with the one task you already do every month.",
                "first_proof": "Run it once on last month's export as a test.",
            }
        ],
        "do_this_today": {
            "action": "Upload last month's NetSuite export to try the reconciliation flow.",
            "time_required": "10 minutes",
            "why_this_one": "It's the task costing you the most time right now.",
        },
    },
}


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), first_name="Aaron", last_name="Neuville")


def _conversation(*, summary: dict[str, object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), kind="interview", summary=summary)


def _ready_rows() -> list[SimpleNamespace]:
    """A transcript the playbook endpoint accepts: the interviewer made its offer."""
    return [
        SimpleNamespace(role="assistant", content="Hi, what do you do?"),
        SimpleNamespace(role="user", content="I run the monthly close."),
        SimpleNamespace(role="assistant", content="Shall I build it?\n[[READY_TO_BUILD]]"),
    ]


def _service(llm: object) -> tuple[InterviewService, AsyncMock, AsyncMock, AsyncMock]:
    conversations = AsyncMock(spec=AbstractConversationRepository)
    messages = AsyncMock(spec=AbstractMessageRepository)
    context = AsyncMock(spec=InterviewContextService)
    context.build_assessment_context.return_value = "ASSESSMENT"
    service = InterviewService(conversations, messages, llm, context)  # ty: ignore[invalid-argument-type]
    return service, conversations, messages, context


class _FlakyLlmClient:
    """complete_structured returns each queued result in turn (retry tests)."""

    model = "fake-model"

    def __init__(self, results: list[dict[str, object]]) -> None:
        self._results = list(results)
        self.calls = 0

    async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
        self.calls += 1
        result = self._results.pop(0)
        return result, LlmUsage(input_tokens=10, output_tokens=10)


async def test_build_playbook_persists_and_returns_shared_only() -> None:
    llm = FakeLlmClient(chunks=[], structured=_EXTRACTION)
    service, conversations, messages, _context = _service(llm)
    conversation = _conversation(summary=None)
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = _ready_rows()
    user = _user()

    result = await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

    assert isinstance(result, PlaybookShared)
    assert not hasattr(result, "internal")
    conversations.update_summary.assert_awaited_once()
    call = conversations.update_summary.await_args
    assert call.args[0] == conversation.id
    persisted = call.args[1]
    assert set(persisted.keys()) == {"internal", "shared", "meta"}
    meta = persisted["meta"]
    assert meta["model"] == "fake-model"
    assert meta["prompt_version"] == prompt_version("interview_playbook")
    assert meta["interview_prompt_version"] == prompt_version("interview")
    assert meta["thinking"] == "disabled"
    assert meta["attempts"] == 1
    assert meta["usage"] == {"input_tokens": 10, "output_tokens": 0}
    assert meta["max_tokens"] == 8192


async def test_build_playbook_idempotent() -> None:
    llm = FakeLlmClient(chunks=[])
    service, conversations, _messages, _context = _service(llm)
    conversation = _conversation(summary=_EXTRACTION)
    conversations.list_for_user.return_value = [conversation]
    user = _user()

    result = await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

    assert isinstance(result, PlaybookShared)
    assert llm.structured_calls == []
    conversations.update_summary.assert_not_awaited()


async def test_build_playbook_retries_once_then_succeeds() -> None:
    llm = _FlakyLlmClient([{}, _EXTRACTION])
    service, conversations, messages, _context = _service(llm)
    conversation = _conversation(summary=None)
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = _ready_rows()
    user = _user()

    result = await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

    assert isinstance(result, PlaybookShared)
    assert llm.calls == 2
    assert conversations.update_summary.await_args.args[1]["meta"]["attempts"] == 2


async def test_build_playbook_raises_after_two_failures() -> None:
    llm = _FlakyLlmClient([{}, {}])
    service, conversations, messages, _context = _service(llm)
    conversation = _conversation(summary=None)
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = _ready_rows()
    user = _user()

    with pytest.raises(DomainError):
        await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

    assert llm.calls == 2


async def test_get_state_transitions() -> None:
    llm = FakeLlmClient(chunks=[])
    service, conversations, _messages, _context = _service(llm)
    user = _user()

    conversations.list_for_user.return_value = []
    state = await service.get_state(user=user)  # ty: ignore[invalid-argument-type]
    assert state.status == "not_started"
    assert state.conversation_id is None
    assert state.playbook is None

    in_progress_conv = _conversation(summary=None)
    conversations.list_for_user.return_value = [in_progress_conv]
    state = await service.get_state(user=user)  # ty: ignore[invalid-argument-type]
    assert state.status == "in_progress"
    assert state.conversation_id == in_progress_conv.id
    assert state.playbook is None

    complete_conv = _conversation(summary=_EXTRACTION)
    conversations.list_for_user.return_value = [complete_conv]
    state = await service.get_state(user=user)  # ty: ignore[invalid-argument-type]
    assert state.status == "complete"
    assert state.conversation_id == complete_conv.id
    assert isinstance(state.playbook, PlaybookShared)


async def test_status_for_reflects_conversation_state() -> None:
    llm = FakeLlmClient(chunks=[])
    service, conversations, _messages, _context = _service(llm)
    user = _user()

    conversations.list_for_user.return_value = []
    assert await service.status_for(user=user) == "not_started"  # ty: ignore[invalid-argument-type]

    conversations.list_for_user.return_value = [_conversation(summary=None)]
    assert await service.status_for(user=user) == "in_progress"  # ty: ignore[invalid-argument-type]

    conversations.list_for_user.return_value = [_conversation(summary=_EXTRACTION)]
    assert await service.status_for(user=user) == "complete"  # ty: ignore[invalid-argument-type]


async def test_get_admin_view_returns_both_boxes_and_tier() -> None:
    llm = FakeLlmClient(chunks=[])
    service, conversations, messages, _context = _service(llm)
    conversation = _conversation(summary=_EXTRACTION)
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = [
        SimpleNamespace(role="user", content="hi"),
        SimpleNamespace(role="assistant", content="hello"),
    ]

    result = await service.get_admin_view(user_id=uuid.uuid4())

    assert result.status == "complete"
    assert isinstance(result.internal, PlaybookInternal)
    assert isinstance(result.shared, PlaybookShared)
    assert result.tier == _EXTRACTION["internal"]["input_quality"]["tier"]  # ty: ignore[not-subscriptable]
    assert len(result.transcript) == 2
    assert result.transcript[0].role == "user"
    assert result.transcript[0].content == "hi"
    assert result.transcript[1].role == "assistant"
    assert result.transcript[1].content == "hello"


async def test_get_admin_view_not_started() -> None:
    llm = FakeLlmClient(chunks=[])
    service, conversations, _messages, _context = _service(llm)
    conversations.list_for_user.return_value = []

    result = await service.get_admin_view(user_id=uuid.uuid4())

    assert result.status == "not_started"
    assert result.internal is None
    assert result.shared is None
    assert result.transcript == []


async def test_reset_deletes_all_interview_conversations() -> None:
    llm = FakeLlmClient(chunks=[])
    service, conversations, _messages, _context = _service(llm)
    conv_a = _conversation()
    conv_b = _conversation()
    conversations.list_for_user.return_value = [conv_a, conv_b]

    await service.reset(user_id=uuid.uuid4())

    assert conversations.delete.await_count == 2
    conversations.delete.assert_any_await(conv_a.id)
    conversations.delete.assert_any_await(conv_b.id)


async def test_generate_retries_on_llm_error_then_succeeds() -> None:
    class _FakeLlmErrorThenSuccess:
        """First call raises LlmError, second returns the valid extraction."""

        model = "fake-model"

        def __init__(self) -> None:
            self.calls = 0

        async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
            self.calls += 1
            if self.calls == 1:
                raise LlmError("temporary failure")
            return _EXTRACTION, LlmUsage(input_tokens=10, output_tokens=10)

    llm = _FakeLlmErrorThenSuccess()
    service, conversations, messages, _context = _service(llm)
    conversation = _conversation(summary=None)
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = _ready_rows()
    user = _user()

    result = await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

    assert isinstance(result, PlaybookShared)
    assert llm.calls == 2


async def test_build_playbook_strips_ready_marker_from_transcript() -> None:
    # The interviewer appends [[READY_TO_BUILD]] to its build-offer turn (a UI signal);
    # it must not bleed into the generation transcript.
    llm = FakeLlmClient(chunks=[], structured=_EXTRACTION)
    service, conversations, messages, _context = _service(llm)
    conversation = _conversation(summary=None)
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = [
        SimpleNamespace(role="user", content="hi"),
        SimpleNamespace(
            role="assistant",
            content="Great — want me to build your playbook?\n[[READY_TO_BUILD]]",
        ),
    ]
    user = _user()

    await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

    system = llm.structured_calls[0]["system"]
    assert isinstance(system, str)
    assert "[[READY_TO_BUILD]]" not in system
    assert "want me to build your playbook?" in system


async def test_get_admin_view_strips_ready_marker_from_transcript() -> None:
    llm = FakeLlmClient(chunks=[])
    service, conversations, messages, _context = _service(llm)
    conversation = _conversation(summary=_EXTRACTION)
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = [
        SimpleNamespace(role="assistant", content="Ready when you are.\n[[READY_TO_BUILD]]"),
    ]

    result = await service.get_admin_view(user_id=uuid.uuid4())

    assert result.transcript[0].content == "Ready when you are."


async def test_build_playbook_strips_em_and_en_dashes() -> None:
    import copy

    dirty = copy.deepcopy(_EXTRACTION)
    dirty["shared"]["where_you_are_today"] = "You save time — a lot of it."  # ty: ignore[invalid-assignment]
    dirty["internal"]["company_context"] = "Finance team – mid-size, inferred."  # ty: ignore[invalid-assignment]
    llm = FakeLlmClient(chunks=[], structured=dirty)
    service, conversations, messages, _context = _service(llm)
    conversation = _conversation(summary=None)
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = _ready_rows()
    user = _user()

    result = await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

    assert "—" not in result.where_you_are_today
    assert "–" not in result.where_you_are_today
    assert "-" in result.where_you_are_today
    persisted = conversations.update_summary.await_args.args[1]
    blob = json.dumps(persisted, ensure_ascii=False)
    assert "—" not in blob and "–" not in blob


async def test_open_interview_fresh_generates_persists_and_returns_greeting() -> None:
    llm = FakeLlmClient(chunks=["Hi Aaron, ", "shall we begin?"])
    service, conversations, messages, context = _service(llm)
    context.build_briefing.return_value = "BRIEFING"
    conversations.list_for_user.return_value = []
    new_conv = _conversation(summary=None)
    conversations.create_interview_if_absent.return_value = new_conv
    user = _user()

    result = await service.open_interview(user=user)  # ty: ignore[invalid-argument-type]

    assert isinstance(result, InterviewOpenerResponse)
    assert result.conversation_id == new_conv.id
    assert result.greeting == "Hi Aaron, shall we begin?"
    # only the assistant greeting is persisted (no user turn)
    messages.create.assert_awaited_once()
    _pos, kw = messages.create.await_args.args, messages.create.await_args.kwargs
    assert kw["role"] == "assistant"
    assert kw["content"] == "Hi Aaron, shall we begin?"
    assert kw["metadata"] == {"model": "fake-model", "prompt_version": prompt_version("interview")}
    # the model saw a synthetic user kickoff and the briefing-grounded system prompt
    call = llm.calls[0]
    assert call["messages"][0]["role"] == "user"  # ty: ignore[not-subscriptable]
    assert "BRIEFING" in call["system"]  # ty: ignore[unsupported-operator]


async def test_open_interview_idempotent_returns_existing_greeting() -> None:
    llm = FakeLlmClient(chunks=["should not stream"])
    service, conversations, messages, _context = _service(llm)
    existing = _conversation(summary=None)
    conversations.list_for_user.return_value = [existing]
    messages.list_for_conversation.return_value = [
        SimpleNamespace(role="assistant", content="Hi Aaron, welcome back."),
    ]
    user = _user()

    result = await service.open_interview(user=user)  # ty: ignore[invalid-argument-type]

    assert result.conversation_id == existing.id
    assert result.greeting == "Hi Aaron, welcome back."
    assert llm.calls == []
    conversations.create_interview_if_absent.assert_not_awaited()
    messages.create.assert_not_awaited()


async def test_open_interview_losing_the_race_returns_the_winners_conversation() -> None:
    """Two concurrent openers both pass the "no interview yet" check; the partial
    unique index lets only one insert through. The loser returns the winner's
    conversation and greeting, persisting nothing of its own."""
    llm = FakeLlmClient(chunks=["Hi Aaron, ", "shall we begin?"])
    service, conversations, messages, context = _service(llm)
    context.build_briefing.return_value = "BRIEFING"
    winner = _conversation(summary=None)
    conversations.list_for_user.side_effect = [[], [winner]]
    conversations.create_interview_if_absent.return_value = None
    messages.list_for_conversation.return_value = [
        SimpleNamespace(role="assistant", content="Hi Aaron, the winner's greeting."),
    ]
    user = _user()

    result = await service.open_interview(user=user)  # ty: ignore[invalid-argument-type]

    assert result.conversation_id == winner.id
    assert result.greeting == "Hi Aaron, the winner's greeting."
    conversations.create_interview_if_absent.assert_awaited_once_with(user.id)
    messages.create.assert_not_awaited()
    conversations.touch.assert_not_awaited()


async def test_open_interview_losing_before_the_winners_greeting_lands_is_empty() -> None:
    """The winner inserts the conversation before its greeting row: a loser that
    reads in between gets the conversation with an empty greeting (the page
    re-reads it via GET /api/interview/me)."""
    service, conversations, messages, context = _service(FakeLlmClient(chunks=["Hi"]))
    context.build_briefing.return_value = "BRIEFING"
    winner = _conversation(summary=None)
    conversations.list_for_user.side_effect = [[], [winner]]
    conversations.create_interview_if_absent.return_value = None
    messages.list_for_conversation.return_value = []

    result = await service.open_interview(user=_user())  # ty: ignore[invalid-argument-type]

    assert result.conversation_id == winner.id
    assert result.greeting == ""
    messages.create.assert_not_awaited()


async def test_open_interview_winner_reset_mid_race_is_a_retryable_conflict() -> None:
    """Lost the insert race, then the winner's interview was reset before the
    re-read: nothing to return, so a 409 the page can retry."""
    service, conversations, messages, context = _service(FakeLlmClient(chunks=["Hi"]))
    context.build_briefing.return_value = "BRIEFING"
    conversations.list_for_user.side_effect = [[], []]
    conversations.create_interview_if_absent.return_value = None

    with pytest.raises(ConflictError):
        await service.open_interview(user=_user())  # ty: ignore[invalid-argument-type]
    messages.create.assert_not_awaited()


async def test_open_interview_llm_failure_creates_no_conversation() -> None:
    exc = status_error(anthropic.AuthenticationError, 401)
    service, conversations, messages, context = _service(_FailingStreamingLlmClient(exc))
    context.build_briefing.return_value = "BRIEFING"
    conversations.list_for_user.return_value = []
    user = _user()

    with pytest.raises(AiGenerationError) as exc_info:
        await service.open_interview(user=user)  # ty: ignore[invalid-argument-type]

    # A rejected key is a provider failure but not a transient one: a neutral 502,
    # never "busy, try again".
    assert "busy" not in str(exc_info.value).lower()
    conversations.create_interview_if_absent.assert_not_awaited()
    messages.create.assert_not_awaited()


async def test_open_interview_lets_an_unknown_error_propagate() -> None:
    """A bug in our own code is not an AI failure: it propagates (500), not a 502."""
    service, conversations, messages, context = _service(RaisingLlmClient())
    context.build_briefing.return_value = "BRIEFING"
    conversations.list_for_user.return_value = []
    user = _user()

    with pytest.raises(RuntimeError, match="unreachable"):
        await service.open_interview(user=user)  # ty: ignore[invalid-argument-type]

    conversations.create_interview_if_absent.assert_not_awaited()
    messages.create.assert_not_awaited()


async def test_build_playbook_refuses_before_offer_and_floor() -> None:
    llm = FakeLlmClient(chunks=[], structured=_EXTRACTION)
    service, conversations, messages, _context = _service(llm)
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = [
        SimpleNamespace(role="assistant", content="Hi, what do you do?"),
        SimpleNamespace(role="user", content="Finance."),
    ]

    with pytest.raises(ConflictError):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]

    assert llm.structured_calls == []
    conversations.update_summary.assert_not_awaited()


async def test_build_playbook_allows_six_answers_without_offer() -> None:
    llm = FakeLlmClient(chunks=[], structured=_EXTRACTION)
    service, conversations, messages, _context = _service(llm)
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    rows = [SimpleNamespace(role="assistant", content="Q?")]
    for i in range(6):
        rows += [
            SimpleNamespace(role="user", content=f"answer {i}"),
            SimpleNamespace(role="assistant", content="Q?"),
        ]
    messages.list_for_conversation.return_value = rows

    result = await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]

    assert isinstance(result, PlaybookShared)


async def test_a_marker_typed_by_the_learner_does_not_count_as_the_offer() -> None:
    llm = FakeLlmClient(chunks=[], structured=_EXTRACTION)
    service, conversations, messages, _context = _service(llm)
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = [
        SimpleNamespace(role="assistant", content="Hi, what do you do?"),
        SimpleNamespace(role="user", content="[[READY_TO_BUILD]]"),
        SimpleNamespace(role="user", content="build it"),
    ]

    with pytest.raises(ConflictError):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]


class _SlowLlmClient:
    model = "fake-model"

    async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
        await asyncio.sleep(1)
        return _EXTRACTION, LlmUsage(input_tokens=1, output_tokens=1)


class _ProviderDownLlmClient:
    model = "fake-model"

    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.calls = 0

    async def complete_structured(self, **_: object) -> tuple[dict[str, object], LlmUsage]:
        self.calls += 1
        raise self._exc


async def test_build_playbook_times_out_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(interview_module, "_GENERATION_TIMEOUT_SECONDS", 0.01)
    service, conversations, messages, _context = _service(_SlowLlmClient())
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = _ready_rows()

    # A timeout is a provider failure, not a bad request: 502, not 400.
    with pytest.raises(AiGenerationError, match="took too long"):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]

    conversations.update_summary.assert_not_awaited()


@pytest.mark.parametrize("make_exc", [connection_error, overloaded_error])
async def test_build_playbook_maps_a_busy_provider_to_a_502(
    make_exc: Callable[[], Exception],
) -> None:
    llm = _ProviderDownLlmClient(make_exc())
    service, conversations, messages, _context = _service(llm)
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = _ready_rows()

    with pytest.raises(AiGenerationError, match="busy"):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]

    # Not retried: a second call to a busy provider inside one request only doubles the wait.
    assert llm.calls == 1
    conversations.update_summary.assert_not_awaited()


async def test_build_playbook_maps_a_non_transient_provider_error_to_a_neutral_502(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A rejected key (401) is the provider failing, not a bug: 502, logged as an error
    (type and conversation id only), and no "try again later" wording."""
    exc = status_error(anthropic.AuthenticationError, 401)
    service, conversations, messages, _context = _service(_ProviderDownLlmClient(exc))
    conversation = _conversation(summary=None)
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = _ready_rows()

    with (
        caplog.at_level(logging.WARNING, logger="src.services.interview_service"),
        pytest.raises(AiGenerationError) as exc_info,
    ):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]

    assert "busy" not in str(exc_info.value).lower()
    records = [r for r in caplog.records if r.name == "src.services.interview_service"]
    assert [r.levelname for r in records] == ["ERROR"]
    assert "AuthenticationError" in records[0].getMessage()
    assert str(conversation.id) in records[0].getMessage()
    assert "monthly close" not in caplog.text


async def test_build_playbook_lets_an_unknown_error_propagate() -> None:
    service, conversations, messages, _context = _service(
        _ProviderDownLlmClient(RuntimeError("bug"))
    )
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = _ready_rows()

    with pytest.raises(RuntimeError, match="bug"):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]


async def test_build_playbook_refuses_an_oversized_transcript() -> None:
    llm = FakeLlmClient(chunks=[], structured=_EXTRACTION)
    service, conversations, messages, _context = _service(llm)
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = [
        *_ready_rows(),
        SimpleNamespace(role="user", content="x" * 100_001),
    ]

    with pytest.raises(DomainError, match="too long"):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]

    assert llm.structured_calls == []


async def test_open_interview_failure_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    llm = _FailingStreamingLlmClient(overloaded_error())
    service, conversations, _messages, context = _service(llm)
    context.build_briefing.return_value = "BRIEFING"
    conversations.list_for_user.return_value = []

    with caplog.at_level(logging.WARNING), pytest.raises(AiGenerationError):
        await service.open_interview(user=_user())  # ty: ignore[invalid-argument-type]

    assert "interview opener failed" in caplog.text


async def test_generation_failure_logs_never_include_model_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Both attempts return schema-invalid dicts carrying a distinctive marker in the
    # (rejected) model output. The marker must never reach the logs, even though the
    # attempt itself is logged.
    llm = _FlakyLlmClient(
        [{"shared": {"secret_marker_text": "LEAKME"}}, {"shared": {"secret_marker_text": "LEAKME"}}]
    )
    service, conversations, messages, _context = _service(llm)
    conversations.list_for_user.return_value = [_conversation(summary=None)]
    messages.list_for_conversation.return_value = _ready_rows()

    with caplog.at_level(logging.WARNING), pytest.raises(DomainError):
        await service.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]

    assert "LEAKME" not in caplog.text
    assert "playbook attempt 1 unusable" in caplog.text
    assert "playbook attempt 2 unusable" in caplog.text


class _SlowStreamManager:
    async def __aenter__(self) -> _SlowStreamManager:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def __aiter__(self) -> AsyncIterator[str]:
        await asyncio.sleep(1)
        yield "too late"

    async def usage(self) -> LlmUsage:
        return LlmUsage(input_tokens=0, output_tokens=0)


class _SlowStreamingLlmClient:
    model = "fake-model"

    def stream_reply(self, **_: object) -> _SlowStreamManager:
        return _SlowStreamManager()


async def test_opener_is_bounded_by_its_own_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(interview_module, "_OPENER_TIMEOUT_SECONDS", 0.01)
    service, conversations, messages, context = _service(_SlowStreamingLlmClient())
    context.build_briefing.return_value = "BRIEFING"
    conversations.list_for_user.return_value = []

    with pytest.raises(AiGenerationError):
        await service.open_interview(user=_user())  # ty: ignore[invalid-argument-type]

    conversations.create_interview_if_absent.assert_not_awaited()
    messages.create.assert_not_awaited()


class _FailingStreamManager:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __aenter__(self) -> _FailingStreamManager:
        raise self._exc

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _FailingStreamingLlmClient:
    model = "fake-model"

    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def stream_reply(self, **_: object) -> _FailingStreamManager:
        return _FailingStreamManager(self._exc)


@pytest.mark.parametrize("make_exc", [connection_error, overloaded_error])
async def test_opener_transient_provider_failure_is_a_busy_502(
    make_exc: Callable[[], Exception],
) -> None:
    exc = make_exc()
    service, conversations, messages, context = _service(_FailingStreamingLlmClient(exc))
    context.build_briefing.return_value = "BRIEFING"
    conversations.list_for_user.return_value = []

    with pytest.raises(AiGenerationError, match="busy"):
        await service.open_interview(user=_user())  # ty: ignore[invalid-argument-type]

    conversations.create_interview_if_absent.assert_not_awaited()
    messages.create.assert_not_awaited()
