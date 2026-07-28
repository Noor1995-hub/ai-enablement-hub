"""InterviewService: wrap-up generation (retry-once structured LLM call),
state derivation, admin view, and reset. Pure-logic unit tests with mocked
repositories/services (AAA, no DB)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
from src.schemas.interview import PlaybookShared
from src.services.exceptions import DomainError
from src.services.interview_context import InterviewContextService
from src.services.interview_service import InterviewService
from src.services.llm_service import LlmUsage
from tests.fixtures.llm import FakeLlmClient

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


def _service(llm: object) -> tuple[InterviewService, AsyncMock, AsyncMock, AsyncMock]:
    conversations = AsyncMock(spec=AbstractConversationRepository)
    messages = AsyncMock(spec=AbstractMessageRepository)
    context = AsyncMock(spec=InterviewContextService)
    context.build_assessment_context.return_value = "ASSESSMENT"
    service = InterviewService(conversations, messages, llm, context)  # ty: ignore[invalid-argument-type]
    return service, conversations, messages, context


class _FlakyLlmClient:
    """complete_structured returns each queued result in turn (retry tests)."""

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
    messages.list_for_conversation.return_value = [
        SimpleNamespace(role="user", content="hi"),
        SimpleNamespace(role="assistant", content="hello"),
    ]
    user = _user()

    result = await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

    assert isinstance(result, PlaybookShared)
    assert not hasattr(result, "internal")
    conversations.update_summary.assert_awaited_once()
    call = conversations.update_summary.await_args
    assert call.args[0] == conversation.id
    persisted = call.args[1]
    assert set(persisted.keys()) == {"internal", "shared"}


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
    messages.list_for_conversation.return_value = []
    user = _user()

    result = await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

    assert isinstance(result, PlaybookShared)
    assert llm.calls == 2


async def test_build_playbook_raises_after_two_failures() -> None:
    llm = _FlakyLlmClient([{}, {}])
    service, conversations, messages, _context = _service(llm)
    conversation = _conversation(summary=None)
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = []
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
