from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from src.repositories.base import AbstractFeedbackRepository
from src.services.feedback_triage_service import FeedbackTriageService
from src.services.llm_service import LlmUsage


class _ScriptedLlm:
    """Returns (or raises) one scripted result per complete_structured call."""

    def __init__(self, results: list[dict[str, Any] | Exception]) -> None:
        self._results = list(results)
        self.prompts: list[str] = []
        self.systems: list[str] = []

    async def complete_structured(
        self, *, system: str, prompt: str, schema: object, max_tokens: int
    ) -> tuple[dict[str, Any], LlmUsage]:
        self.systems.append(system)
        self.prompts.append(prompt)
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result, LlmUsage(input_tokens=10, output_tokens=5)


def _row(message: str = "The examples were unclear") -> tuple[Any, Any]:
    feedback = SimpleNamespace(id=uuid.uuid4(), message=message)
    lesson = SimpleNamespace(
        id=uuid.uuid4(),
        title="Prompting basics",
        content_blocks=[{"id": "b1", "type": "paragraph", "text": "Be specific."}],
    )
    return feedback, lesson


def _repo(rows: list[tuple[Any, Any]], remaining: int = 0) -> AsyncMock:
    repo = AsyncMock(spec=AbstractFeedbackRepository)
    repo.list_awaiting_suggestion.return_value = rows
    repo.count_awaiting_suggestion.return_value = remaining
    return repo


async def test_writes_the_suggestion_and_never_the_status() -> None:
    feedback, lesson = _row()
    repo = _repo([(feedback, lesson)])
    llm = _ScriptedLlm([{"suggested_status": "accepted", "rationale": "Asks for an example."}])
    service = FeedbackTriageService(repo, llm)  # ty: ignore[invalid-argument-type]

    suggested, remaining = await service.suggest(limit=5)

    assert (suggested, remaining) == (1, 0)
    repo.set_ai_suggestion.assert_awaited_once_with(
        feedback, suggested_status="accepted", rationale="Asks for an example."
    )
    # The iron rule of this feature: triage suggests, the admin decides.
    repo.set_status.assert_not_awaited()


async def test_prompt_carries_the_lesson_and_the_feedback() -> None:
    feedback, lesson = _row("Please add a worked example")
    repo = _repo([(feedback, lesson)])
    llm = _ScriptedLlm([{"suggested_status": "accepted", "rationale": "Actionable."}])
    service = FeedbackTriageService(repo, llm)  # ty: ignore[invalid-argument-type]

    await service.suggest(limit=5)

    prompt = llm.prompts[0]
    assert "Prompting basics" in prompt
    assert "Please add a worked example" in prompt
    assert "Be specific." in prompt
    assert "triage" in llm.systems[0].lower()


async def test_malformed_output_is_skipped_not_written() -> None:
    feedback, lesson = _row()
    repo = _repo([(feedback, lesson)], remaining=1)
    llm = _ScriptedLlm([{"suggested_status": "maybe", "rationale": "hmm"}])
    service = FeedbackTriageService(repo, llm)  # ty: ignore[invalid-argument-type]

    suggested, remaining = await service.suggest(limit=5)

    assert (suggested, remaining) == (0, 1)
    repo.set_ai_suggestion.assert_not_awaited()


async def test_one_failing_row_does_not_abort_the_batch() -> None:
    first, lesson_a = _row("first")
    second, lesson_b = _row("second")
    repo = _repo([(first, lesson_a), (second, lesson_b)])
    llm = _ScriptedLlm(
        [
            RuntimeError("Anthropic API unreachable"),
            {"suggested_status": "dismissed", "rationale": "Off topic."},
        ]
    )
    service = FeedbackTriageService(repo, llm)  # ty: ignore[invalid-argument-type]

    suggested, _remaining = await service.suggest(limit=5)

    assert suggested == 1
    repo.set_ai_suggestion.assert_awaited_once_with(
        second, suggested_status="dismissed", rationale="Off topic."
    )


async def test_empty_queue_makes_no_model_calls() -> None:
    repo = _repo([])
    llm = _ScriptedLlm([])
    service = FeedbackTriageService(repo, llm)  # ty: ignore[invalid-argument-type]

    assert await service.suggest(limit=5) == (0, 0)
    assert llm.prompts == []


async def test_limit_and_project_scope_are_passed_through() -> None:
    repo = _repo([])
    project_id = uuid.uuid4()
    service = FeedbackTriageService(repo, _ScriptedLlm([]))  # ty: ignore[invalid-argument-type]

    await service.suggest(project_id=project_id, limit=3)

    repo.list_awaiting_suggestion.assert_awaited_once_with(project_id=project_id, limit=3)
    repo.count_awaiting_suggestion.assert_awaited_once_with(project_id=project_id)
