"""Golden case for feedback triage: pins exactly what the feature sends the model.

Fixtures are fictional and fully deterministic (fixed UUIDs, no wall-clock reads) so the
snapshot never drifts for reasons unrelated to a real prompt change.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from src.repositories.base import AbstractFeedbackRepository
from src.services.feedback_triage_service import FeedbackTriageService
from tests.golden.ai.harness import RecordingLlm, assert_golden, render_calls


def _row(message: str) -> tuple[Any, Any]:
    feedback = SimpleNamespace(id=uuid.UUID(int=1), message=message)
    lesson = SimpleNamespace(
        id=uuid.UUID(int=2),
        title="Prompting basics",
        content_blocks=[{"id": "b1", "type": "paragraph", "text": "Be specific."}],
    )
    return feedback, lesson


def _repo(rows: list[tuple[Any, Any]], remaining: int = 0) -> AsyncMock:
    repo = AsyncMock(spec=AbstractFeedbackRepository)
    repo.list_awaiting_suggestion.return_value = rows
    repo.count_awaiting_suggestion.return_value = remaining
    return repo


async def test_feedback_triage_golden() -> None:
    feedback, lesson = _row("Please add a worked example")
    repo = _repo([(feedback, lesson)])
    llm = RecordingLlm(
        structured_results=[{"suggested_status": "accepted", "rationale": "Actionable."}]
    )
    service = FeedbackTriageService(repo, llm)

    await service.suggest(limit=5)

    assert_golden("feedback_triage", llm.calls)

    # determinism (Review Focus 3): a second identical run renders identically
    feedback2, lesson2 = _row("Please add a worked example")
    repo2 = _repo([(feedback2, lesson2)])
    second_run_llm = RecordingLlm(
        structured_results=[{"suggested_status": "accepted", "rationale": "Actionable."}]
    )
    service2 = FeedbackTriageService(repo2, second_run_llm)
    await service2.suggest(limit=5)

    assert render_calls(llm.calls) == render_calls(second_run_llm.calls)
