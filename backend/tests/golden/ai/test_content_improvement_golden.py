"""Golden cases for content improvement: the drafting call (house style +
calibration notes + the drafting prompt) and the critique call over a fixed
draft/accepted pair.

Fixtures are fictional and fully deterministic (fixed UUIDs, no wall-clock
reads) so the snapshot never drifts for reasons unrelated to a real prompt
change.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from src.repositories.base import (
    AbstractCalibrationNoteRepository,
    AbstractContentRepository,
    AbstractFeedbackRepository,
    AbstractProposalRepository,
    AbstractUnitOfWork,
)
from src.services.content_improvement_service import ContentImprovementService
from tests.golden.ai.harness import RecordingLlm, assert_golden, render_calls

_LESSON_ID = uuid.UUID(int=30)
_FEEDBACK_ID = uuid.UUID(int=31)
_PROPOSAL_ID = uuid.UUID(int=32)

# A small fictional lesson whose card_group already carries nested ids on its
# cards, so this pins the ordinary path (no `normalise_nested_ids` repair),
# not the legacy id-backfill one covered by the unit tests.
_BLOCKS: list[dict[str, Any]] = [
    {"id": "b1", "type": "heading", "level": 2, "text": "Prompting basics"},
    {"id": "b2", "type": "paragraph", "text": "Be specific, and give a real example."},
    {
        "id": "b3",
        "type": "card_group",
        "cards": [
            {"id": "b3-card-a", "title": "Give context", "body": "Say who the reader is."},
            {"id": "b3-card-b", "title": "Give an example", "body": "Show, do not just tell."},
        ],
    },
]

_NOTE_ONE = "Prefer inline bullets over a card group for a short enumeration."
_NOTE_TWO = "Keep the opening paragraph under three sentences."


def _lesson() -> Any:
    return SimpleNamespace(id=_LESSON_ID, title="Prompting basics", content_blocks=_BLOCKS)


def _feedback() -> Any:
    return SimpleNamespace(id=_FEEDBACK_ID, message="Could you add a worked example up top?")


def _content_improvement_service(
    llm: RecordingLlm,
) -> tuple[ContentImprovementService, Any]:
    lesson = _lesson()
    feedback = _feedback()
    proposals = AsyncMock(spec=AbstractProposalRepository)
    proposals.covered_feedback_ids.return_value = set()
    feedback_repo = AsyncMock(spec=AbstractFeedbackRepository)
    feedback_repo.list_accepted_with_lesson.return_value = [(feedback, lesson)]
    content = AsyncMock(spec=AbstractContentRepository)
    content.lesson_context.return_value = {}
    notes = AsyncMock(spec=AbstractCalibrationNoteRepository)
    notes.list_for_injection.return_value = [_NOTE_ONE, _NOTE_TWO]
    service = ContentImprovementService(
        proposals,
        feedback_repo,
        content,
        llm,
        notes,
        AsyncMock(spec=AbstractUnitOfWork),
    )
    return service, lesson


async def test_content_improvement_golden() -> None:
    llm = RecordingLlm(
        structured_results=[
            {
                "proposed_blocks": _BLOCKS,
                "summary": "Added a worked example to the opening paragraph.",
            }
        ]
    )
    service, lesson = _content_improvement_service(llm)

    outcome = await service.run(lesson_ids=[lesson.id])

    assert (outcome.proposed, outcome.skipped, outcome.deferred) == (1, 0, 0)
    assert_golden("content_improvement", llm.calls)

    system = llm.calls[0]["system"]
    # A distinctive line from house_style.md.
    assert "The rules below define what good lesson content looks like in this hub." in system
    # A distinctive line from content_improvement.md.
    assert "You revise lessons in delaware's AI Enablement Hub using learner feedback." in system
    # Both fixed calibration notes.
    assert _NOTE_ONE in system
    assert _NOTE_TWO in system

    # determinism: a second, fully independent run renders identically
    llm2 = RecordingLlm(
        structured_results=[
            {
                "proposed_blocks": _BLOCKS,
                "summary": "Added a worked example to the opening paragraph.",
            }
        ]
    )
    service2, lesson2 = _content_improvement_service(llm2)
    await service2.run(lesson_ids=[lesson2.id])
    assert render_calls(llm.calls) == render_calls(llm2.calls)


_DRAFTED = [{"id": "b1", "type": "paragraph", "text": "The agent's original wording."}]
_ACCEPTED = [{"id": "b1", "type": "paragraph", "text": "The admin's preferred wording."}]
_LEARN_CARD: dict[str, Any] = {
    "what_agent_got_wrong": "I reached for a longer paragraph where one short line would do.",
    "what_admin_preferred": "A single short paragraph, no throat clearing.",
    "calibration_notes": [
        "Say the point in one sentence before adding detail.",
        "Prefer a short paragraph over a longer one when both say the same thing.",
    ],
}


def _proposal() -> Any:
    return SimpleNamespace(
        id=_PROPOSAL_ID,
        lesson_id=_LESSON_ID,
        proposed_blocks=_DRAFTED,
        edited_blocks=_ACCEPTED,
        base_blocks=[],
        status="approved",
        critiqued_at=None,
    )


def _critique_service(llm: RecordingLlm) -> tuple[ContentImprovementService, Any]:
    proposal = _proposal()
    proposals = AsyncMock(spec=AbstractProposalRepository)
    proposals.get_by_id.return_value = proposal
    notes = AsyncMock(spec=AbstractCalibrationNoteRepository)
    notes.create_many.return_value = []
    notes.list_for_proposal.return_value = []
    service = ContentImprovementService(
        proposals,
        AsyncMock(spec=AbstractFeedbackRepository),
        AsyncMock(spec=AbstractContentRepository),
        llm,
        notes,
        AsyncMock(spec=AbstractUnitOfWork),
    )
    return service, proposal


async def test_content_improvement_critique_golden() -> None:
    llm = RecordingLlm(structured_results=[_LEARN_CARD])
    service, proposal = _critique_service(llm)

    await service.critique(proposal_id=proposal.id)

    assert_golden("content_improvement_critique", llm.calls)

    system = llm.calls[0]["system"]
    # A distinctive line from content_improvement_critique.md.
    assert "an admin changed it before" in system
    assert "you are now\nlooking at both versions so you can get closer next time." in system
    # The critique agent must NOT be given the house style — it writes no lesson content.
    assert "The rules below define what good lesson content looks like in this hub." not in system

    # determinism: a second, fully independent run renders identically
    llm2 = RecordingLlm(structured_results=[_LEARN_CARD])
    service2, proposal2 = _critique_service(llm2)
    await service2.critique(proposal_id=proposal2.id)
    assert render_calls(llm.calls) == render_calls(llm2.calls)
