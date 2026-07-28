from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from typing import Any
from unittest import mock
from unittest.mock import AsyncMock

from src.repositories.base import (
    AbstractContentRepository,
    AbstractFeedbackRepository,
    AbstractProposalRepository,
)
from src.services import content_improvement_service
from src.services.content_improvement_service import ContentImprovementService
from src.services.llm_service import LlmUsage

_GOOD_BLOCKS = [
    {"id": "b1", "type": "heading", "level": 2, "text": "Prompting basics"},
    {"id": "b2", "type": "paragraph", "text": "Be specific, and give an example."},
]


class _ScriptedLlm:
    """One scripted result (or raise) per complete_structured call."""

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
        return result, LlmUsage(input_tokens=800, output_tokens=400)


def _lesson(title: str = "Prompting basics", blocks: list[Any] | None = None) -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        title=title,
        content_blocks=[{"id": "b1", "type": "paragraph", "text": "Old text."}]
        if blocks is None
        else blocks,
    )


def _feedback(message: str) -> Any:
    return SimpleNamespace(id=uuid.uuid4(), message=message)


def _service(
    pairs: list[tuple[Any, Any]],
    covered: set[uuid.UUID] | None = None,
    llm: _ScriptedLlm | None = None,
) -> tuple[ContentImprovementService, AsyncMock, AsyncMock]:
    proposals = AsyncMock(spec=AbstractProposalRepository)
    proposals.covered_feedback_ids.return_value = covered or set()
    feedback = AsyncMock(spec=AbstractFeedbackRepository)
    feedback.list_accepted_with_lesson.return_value = pairs
    content = AsyncMock(spec=AbstractContentRepository)
    service = ContentImprovementService(
        proposals,
        feedback,
        content,
        llm or _ScriptedLlm([]),  # ty: ignore[invalid-argument-type]
    )
    return service, proposals, content


async def test_drafts_one_proposal_per_lesson_with_provenance() -> None:
    lesson = _lesson()
    one, two = _feedback("too abstract"), _feedback("please add an example")
    llm = _ScriptedLlm([{"proposed_blocks": _GOOD_BLOCKS, "summary": "Added an example."}])
    service, proposals, content = _service([(one, lesson), (two, lesson)], llm=llm)

    proposed, skipped, remaining = await service.run(max_lessons=3)

    assert (proposed, skipped, remaining) == (1, 0, 0)
    # One call for the lesson, not one per feedback item.
    assert len(llm.prompts) == 1
    proposals.create.assert_awaited_once()
    kwargs = proposals.create.await_args.kwargs
    assert kwargs["lesson_id"] == lesson.id
    assert kwargs["proposed_blocks"] == _GOOD_BLOCKS
    assert kwargs["base_blocks"] == lesson.content_blocks
    assert set(kwargs["source_feedback_ids"]) == {one.id, two.id}
    assert kwargs["summary"] == "Added an example."
    assert kwargs.get("status", "pending") == "pending"
    # Drafting NEVER writes the live lesson.
    content.update_lesson.assert_not_awaited()


async def test_prompt_carries_the_lesson_and_every_feedback_message() -> None:
    lesson = _lesson()
    llm = _ScriptedLlm([{"proposed_blocks": _GOOD_BLOCKS, "summary": "s"}])
    service, _proposals, _content = _service(
        [(_feedback("too abstract"), lesson), (_feedback("add an example"), lesson)], llm=llm
    )

    await service.run(max_lessons=3)

    prompt = llm.prompts[0]
    assert "Prompting basics" in prompt
    assert "Old text." in prompt
    assert "too abstract" in prompt
    assert "add an example" in prompt
    assert "content" in llm.systems[0].lower()


async def test_already_incorporated_feedback_is_not_redrafted() -> None:
    lesson = _lesson()
    done = _feedback("already covered")
    llm = _ScriptedLlm([])
    service, proposals, _content = _service([(done, lesson)], covered={done.id}, llm=llm)

    assert await service.run(max_lessons=3) == (0, 0, 0)
    assert llm.prompts == []
    proposals.create.assert_not_awaited()


async def test_max_lessons_bounds_the_run_and_reports_what_is_left() -> None:
    first, second = _lesson("First"), _lesson("Second")
    llm = _ScriptedLlm([{"proposed_blocks": _GOOD_BLOCKS, "summary": "s"}])
    service, _proposals, _content = _service(
        [(_feedback("a"), first), (_feedback("b"), second)], llm=llm
    )

    assert await service.run(max_lessons=1) == (1, 0, 1)


async def test_invalid_blocks_are_never_stored_as_a_pending_proposal() -> None:
    lesson = _lesson()
    llm = _ScriptedLlm(
        [{"proposed_blocks": [{"id": "b1", "type": "banner", "text": "x"}], "summary": "s"}]
    )
    service, proposals, content = _service([(_feedback("a"), lesson)], llm=llm)

    proposed, skipped, _remaining = await service.run(max_lessons=3)

    assert (proposed, skipped) == (0, 1)
    content.update_lesson.assert_not_awaited()
    # Recorded as a `failed` proposal so this lesson stops re-consuming runs.
    assert proposals.create.await_args.kwargs["status"] == "failed"
    assert "banner" in proposals.create.await_args.kwargs["summary"]


async def test_a_new_media_locator_is_rejected() -> None:
    lesson = _lesson(blocks=[{"id": "b1", "type": "paragraph", "text": "Old text."}])
    invented = [
        {"id": "b1", "type": "paragraph", "text": "New text."},
        {"id": "b2", "type": "image", "blob_path": "images/made-up.png", "alt": "a chart"},
    ]
    llm = _ScriptedLlm([{"proposed_blocks": invented, "summary": "s"}])
    service, proposals, _content = _service([(_feedback("a"), lesson)], llm=llm)

    proposed, skipped, _remaining = await service.run(max_lessons=3)

    assert (proposed, skipped) == (0, 1)
    assert proposals.create.await_args.kwargs["status"] == "failed"
    assert "made-up.png" in proposals.create.await_args.kwargs["summary"]


async def test_an_empty_block_array_is_rejected() -> None:
    lesson = _lesson()
    llm = _ScriptedLlm([{"proposed_blocks": [], "summary": "wiped it"}])
    service, proposals, _content = _service([(_feedback("a"), lesson)], llm=llm)

    proposed, skipped, _remaining = await service.run(max_lessons=3)

    assert (proposed, skipped) == (0, 1)
    assert proposals.create.await_args.kwargs["status"] == "failed"


async def test_a_model_error_is_recorded_and_does_not_abort_the_batch() -> None:
    first, second = _lesson("First"), _lesson("Second")
    llm = _ScriptedLlm(
        [
            RuntimeError("Anthropic API unreachable"),
            {"proposed_blocks": _GOOD_BLOCKS, "summary": "Second one worked."},
        ]
    )
    service, proposals, _content = _service(
        [(_feedback("a"), first), (_feedback("b"), second)], llm=llm
    )

    proposed, skipped, remaining = await service.run(max_lessons=3)

    assert (proposed, skipped, remaining) == (1, 1, 0)
    assert proposals.create.await_count == 2


async def test_an_oversized_lesson_is_skipped_without_a_model_call() -> None:
    huge = _lesson(blocks=[{"id": "b1", "type": "paragraph", "text": "x" * 60_000}])
    llm = _ScriptedLlm([])
    service, proposals, _content = _service([(_feedback("a"), huge)], llm=llm)

    proposed, skipped, _remaining = await service.run(max_lessons=3)

    assert (proposed, skipped) == (0, 1)
    assert llm.prompts == []
    assert proposals.create.await_args.kwargs["status"] == "failed"
    assert "character" in proposals.create.await_args.kwargs["summary"]


async def test_a_hanging_call_times_out_and_counts_as_skipped() -> None:
    lesson = _lesson()

    class _HangingLlm:
        async def complete_structured(
            self, *, system: str, prompt: str, schema: object, max_tokens: int
        ) -> tuple[dict[str, Any], LlmUsage]:
            await asyncio.sleep(3600)
            raise AssertionError("unreachable")

    proposals = AsyncMock(spec=AbstractProposalRepository)
    proposals.covered_feedback_ids.return_value = set()
    feedback = AsyncMock(spec=AbstractFeedbackRepository)
    feedback.list_accepted_with_lesson.return_value = [(_feedback("a"), lesson)]
    service = ContentImprovementService(
        proposals,
        feedback,
        AsyncMock(spec=AbstractContentRepository),
        _HangingLlm(),  # ty: ignore[invalid-argument-type]
    )

    with mock.patch.object(content_improvement_service, "_PER_LESSON_TIMEOUT_SECONDS", 0.01):
        proposed, skipped, _remaining = await service.run(max_lessons=3)

    assert (proposed, skipped) == (0, 1)
    assert proposals.create.await_args.kwargs["status"] == "failed"


async def test_empty_queue_makes_no_model_calls() -> None:
    llm = _ScriptedLlm([])
    service, proposals, _content = _service([], llm=llm)

    assert await service.run(max_lessons=3) == (0, 0, 0)
    assert llm.prompts == []
    proposals.create.assert_not_awaited()
