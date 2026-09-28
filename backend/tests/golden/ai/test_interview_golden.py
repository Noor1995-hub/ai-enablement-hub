"""Golden cases for the interviewer: the opener (with the real briefing appended) and the
playbook-generation call (with all four template tokens substituted).

Fixtures are fictional and fully deterministic (fixed UUIDs, no wall-clock reads): the
briefing/assessment-context text is produced by the REAL InterviewContextService, driven off
fixed fake SurveyService/MaturityService/LearningService results, so the snapshot pins the
actual composed text, not a stand-in.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from src.repositories.base import AbstractConversationRepository, AbstractMessageRepository
from src.services.interview_context import InterviewContextService
from src.services.interview_service import InterviewService
from src.services.learning_service import LearningService
from src.services.maturity_service import MaturityService
from src.services.survey_service import SurveyService
from tests.golden.ai.harness import RecordingLlm, assert_golden, render_calls

_USER_ID = uuid.UUID(int=20)
_CONVERSATION_ID = uuid.UUID(int=21)

_TOKENS = ("{first_name}", "{assessment_json}", "{company_context}", "{transcript}")

# A fully-populated, fictional extraction satisfying PlaybookExtraction — no real names,
# emails or company data.
_EXTRACTION: dict[str, Any] = {
    "internal": {
        "input_quality": {
            "tier": "PARTIAL",
            "evidence": "Named one system (an ERP) and one recurring pain with rough frequency.",
            "what_to_probe_next": ["Which reports the exports feed downstream"],
        },
        "person": {
            "role_reality": "Coordinates monthly reporting for a small ops team.",
            "influence": "Can pilot new tools without sign-off for her own work.",
            "decision_rights": "No budget authority.",
            "champion_potential": "Moderate — open but cautious.",
            "confidence": "medium",
        },
        "pains": [
            {
                "pain": "Re-typing figures from an ERP export into a shared spreadsheet.",
                "evidence": "Described doing this every month before the ops review.",
                "frequency": "monthly",
                "est_time_cost": "about half a day",
                "basis": "stated",
                "confidence": "high",
            }
        ],
        "blockers": {
            "stated": ["not sure what's allowed with company data"],
            "diagnosed": [
                {
                    "type": "governance",
                    "reasoning": "Uncertainty about approved tools, not lack of interest.",
                    "basis": "inferred from hesitation when asked about pasting data",
                    "confidence": "medium",
                }
            ],
        },
        "maturity": {
            "placement": "explorer",
            "behavioural_evidence": "Uses a generic assistant ad hoc, no saved prompts.",
            "vs_self_reported": "matches self-report",
            "trajectory": "ready to move to practitioner with a concrete first win",
        },
        "systems_landscape": [
            {
                "system": "a fictional ERP (Northwind Ledger)",
                "how_used": "Exports a monthly CSV of transaction lines.",
                "implication": "Any automation must start from that CSV export.",
            }
        ],
        "company_context": "Small operations team at a fictional distribution company, "
        "inferred from role description.",
        "engagement_notes": {
            "opportunities": ["Champion for a reporting-automation pilot"],
            "risks": [],
            "follow_up_questions": ["What format does the CSV export use?"],
        },
    },
    "shared": {
        "where_you_are_today": (
            "You've got a clear handle on the monthly reporting cycle, and you're already "
            "curious about where AI tools could help. The re-typing work you described eats "
            "about half a day every month, and that is exactly the kind of task worth "
            "automating first. You are not starting from zero, you already know where the "
            "pain is and roughly how much it costs you."
        ),
        "use_cases": [
            {
                "rank": 1,
                "start_here": True,
                "name": "Automate the monthly export reconciliation",
                "pain_it_kills": "the half day spent re-typing export figures",
                "in_practice": "Upload the CSV export and let an assistant flag mismatches "
                "before the ops review.",
                "before": "Half a day of manual cross-checking.",
                "after": "A short review of the flagged lines.",
                "impact": "Most of a morning back each month.",
                "difficulty": "Quick Win",
                "systems_involved": ["a fictional ERP (Northwind Ledger)"],
                "assumption_to_check": "That the export format stays consistent month to month.",
                "cross_functional": False,
            }
        ],
        "next_moves": [
            {
                "order": 1,
                "move": "Try the reconciliation check on next month's export.",
                "why_now": "It targets the pain you described first.",
                "linked_use_case": 1,
            }
        ],
        "reframes": [
            {
                "their_hesitation": "I'm not sure what's allowed with company data.",
                "the_concern": "Risking a governance misstep by using the wrong tool.",
                "reframe": "Start with the company-approved tool on data you already share "
                "internally today.",
                "first_proof": "Run it once on a report that's already been shared with the team.",
            }
        ],
        "do_this_today": {
            "action": "Ask IT which tool is approved for this kind of export.",
            "time_required": "10 minutes",
            "why_this_one": "It removes the governance blocker before anything else.",
        },
    },
}


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=_USER_ID, first_name="Alex", last_name="Okafor")


def _context() -> InterviewContextService:
    """A real InterviewContextService over fixed fake survey/maturity/learning results, so
    the golden snapshot pins the actual composed briefing/assessment text."""
    survey = SimpleNamespace(
        job_title="Operations Coordinator",
        department="Operations",
        b_freq="WEEKLY",
        b_tools=["CHATGPT"],
        b_setup=["NONE"],
        b_barriers=["NOT_SURE_ALLOWED"],
        q_timesink="Re-typing the monthly ERP export into a shared spreadsheet",
        q_excitement="Not having to manually reconcile numbers every month",
        score_level="explore",
        usage_band="occasional",
        c1_code="PARTIAL",
        c2_code="PARTIAL",
        c3_code="HAVE",
        c4_code="PARTIAL",
        c5_codes=["UNSURE"],
        c6_code="PARTIAL",
    )
    surveys = AsyncMock(spec=SurveyService)
    surveys.get_own.return_value = survey
    maturity = AsyncMock(spec=MaturityService)
    maturity.effective_level.return_value = "explore"
    learning = AsyncMock(spec=LearningService)
    learning.learning_status.return_value = "not_started"
    return InterviewContextService(surveys, maturity, learning)  # ty: ignore[invalid-argument-type]


async def test_interview_golden() -> None:
    llm = RecordingLlm(chunks=["Hi Alex, thanks for making time. ", "Shall we begin?"])
    conversations = AsyncMock(spec=AbstractConversationRepository)
    messages = AsyncMock(spec=AbstractMessageRepository)
    conversations.list_for_user.return_value = []
    new_conversation = SimpleNamespace(
        id=_CONVERSATION_ID, user_id=_USER_ID, kind="interview", summary=None
    )
    conversations.create.return_value = new_conversation
    service = InterviewService(conversations, messages, llm, _context())
    user = _user()

    await service.open_interview(user=user)  # ty: ignore[invalid-argument-type]

    assert_golden("interview", llm.calls)

    # determinism: a second independent run renders identically
    llm2 = RecordingLlm(chunks=["Hi Alex, thanks for making time. ", "Shall we begin?"])
    conversations2 = AsyncMock(spec=AbstractConversationRepository)
    messages2 = AsyncMock(spec=AbstractMessageRepository)
    conversations2.list_for_user.return_value = []
    conversations2.create.return_value = SimpleNamespace(
        id=_CONVERSATION_ID, user_id=_USER_ID, kind="interview", summary=None
    )
    service2 = InterviewService(conversations2, messages2, llm2, _context())
    await service2.open_interview(user=_user())  # ty: ignore[invalid-argument-type]
    assert render_calls(llm.calls) == render_calls(llm2.calls)


async def test_interview_playbook_golden() -> None:
    llm = RecordingLlm(structured_results=[_EXTRACTION])
    conversations = AsyncMock(spec=AbstractConversationRepository)
    messages = AsyncMock(spec=AbstractMessageRepository)
    conversation = SimpleNamespace(
        id=_CONVERSATION_ID, user_id=_USER_ID, kind="interview", summary=None
    )
    conversations.list_for_user.return_value = [conversation]
    messages.list_for_conversation.return_value = [
        SimpleNamespace(
            role="assistant", content="Hi Alex, thanks for making time. Shall we begin?"
        ),
        SimpleNamespace(
            role="user",
            content="Sure — most of my week goes into pulling reports out of our ERP.",
        ),
        SimpleNamespace(
            role="assistant",
            content="Which system is that, by name?\n[[READY_TO_BUILD]]",
        ),
    ]
    service = InterviewService(conversations, messages, llm, _context())
    user = _user()

    await service.build_playbook(user=user)  # ty: ignore[invalid-argument-type]

    assert_golden("interview_playbook", llm.calls)
    for call in llm.calls:
        for token in _TOKENS:
            assert token not in call["system"]

    # determinism: a second independent run renders identically
    llm2 = RecordingLlm(structured_results=[_EXTRACTION])
    conversations2 = AsyncMock(spec=AbstractConversationRepository)
    messages2 = AsyncMock(spec=AbstractMessageRepository)
    conversation2 = SimpleNamespace(
        id=_CONVERSATION_ID, user_id=_USER_ID, kind="interview", summary=None
    )
    conversations2.list_for_user.return_value = [conversation2]
    messages2.list_for_conversation.return_value = [
        SimpleNamespace(
            role="assistant", content="Hi Alex, thanks for making time. Shall we begin?"
        ),
        SimpleNamespace(
            role="user",
            content="Sure — most of my week goes into pulling reports out of our ERP.",
        ),
        SimpleNamespace(
            role="assistant",
            content="Which system is that, by name?\n[[READY_TO_BUILD]]",
        ),
    ]
    service2 = InterviewService(conversations2, messages2, llm2, _context())
    await service2.build_playbook(user=_user())  # ty: ignore[invalid-argument-type]
    assert render_calls(llm.calls) == render_calls(llm2.calls)
