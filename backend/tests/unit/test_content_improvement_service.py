from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from typing import Any
from unittest import mock
from unittest.mock import AsyncMock

import anthropic
import httpx2

from src.repositories.base import (
    AbstractCalibrationNoteRepository,
    AbstractContentRepository,
    AbstractFeedbackRepository,
    AbstractProposalRepository,
)
from src.services import content_improvement_service
from src.services.calibration_prompt import MAX_INJECTED_NOTES
from src.services.content_improvement_service import ContentImprovementService
from src.services.llm_service import LlmUsage
from src.services.prompts import load_prompt

_GOOD_BLOCKS = [
    {"id": "b1", "type": "heading", "level": 2, "text": "Prompting basics"},
    {"id": "b2", "type": "paragraph", "text": "Be specific, and give an example."},
]


def _overloaded() -> Exception:
    """The real 529 a run hits when Anthropic is at capacity."""
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.OverloadedError(
        "Overloaded", response=httpx2.Response(529, request=request), body=None
    )


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


def _notes_repo(approved: list[str] | None = None) -> AsyncMock:
    """A calibration-note repository whose injection read returns real strings.

    A bare AsyncMock would hand `render_calibration_block` a MagicMock, which
    is not what the real repository returns.
    """
    notes = AsyncMock(spec=AbstractCalibrationNoteRepository)
    notes.list_for_injection.return_value = approved or []
    return notes


def _service(
    pairs: list[tuple[Any, Any]],
    covered: set[uuid.UUID] | None = None,
    llm: _ScriptedLlm | None = None,
    notes: AsyncMock | None = None,
) -> tuple[ContentImprovementService, AsyncMock, AsyncMock]:
    proposals = AsyncMock(spec=AbstractProposalRepository)
    proposals.covered_feedback_ids.return_value = covered or set()
    feedback = AsyncMock(spec=AbstractFeedbackRepository)
    feedback.list_accepted_with_lesson.return_value = pairs
    content = AsyncMock(spec=AbstractContentRepository)
    content.lesson_context.return_value = {}
    service = ContentImprovementService(
        proposals,
        feedback,
        content,
        llm or _ScriptedLlm([]),  # ty: ignore[invalid-argument-type]
        notes if notes is not None else _notes_repo(),
    )
    return service, proposals, content


async def test_drafts_one_proposal_per_lesson_with_provenance() -> None:
    lesson = _lesson()
    one, two = _feedback("too abstract"), _feedback("please add an example")
    llm = _ScriptedLlm([{"proposed_blocks": _GOOD_BLOCKS, "summary": "Added an example."}])
    service, proposals, content = _service([(one, lesson), (two, lesson)], llm=llm)

    outcome = await service.run(lesson_ids=[lesson.id])

    assert (outcome.proposed, outcome.skipped, outcome.deferred) == (1, 0, 0)
    assert outcome.not_queued == 0
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


async def test_only_the_selected_lessons_are_drafted() -> None:
    # THE point of explicit selection: a queue of three, one picked, one call.
    wanted, other, third = _lesson("Wanted"), _lesson("Other"), _lesson("Third")
    llm = _ScriptedLlm([{"proposed_blocks": _GOOD_BLOCKS, "summary": "s"}])
    service, proposals, _content = _service(
        [(_feedback("a"), wanted), (_feedback("b"), other), (_feedback("c"), third)], llm=llm
    )

    outcome = await service.run(lesson_ids=[wanted.id])

    assert (outcome.proposed, outcome.skipped, outcome.deferred) == (1, 0, 0)
    # The two lessons the admin did not pick are simply untouched.
    assert outcome.not_queued == 0
    assert len(llm.prompts) == 1
    assert proposals.create.await_args.kwargs["lesson_id"] == wanted.id


async def test_an_id_that_is_no_longer_queued_is_reported_not_silently_dropped() -> None:
    # Two admins with the page open: the other one drafted this lesson already.
    lesson = _lesson()
    llm = _ScriptedLlm([])
    service, proposals, _content = _service([], llm=llm)

    outcome = await service.run(lesson_ids=[lesson.id])

    assert (outcome.proposed, outcome.skipped, outcome.not_queued) == (0, 0, 1)
    assert llm.prompts == []
    proposals.create.assert_not_awaited()


async def test_an_empty_selection_makes_no_model_calls() -> None:
    lesson = _lesson()
    llm = _ScriptedLlm([])
    service, proposals, _content = _service([(_feedback("a"), lesson)], llm=llm)

    outcome = await service.run(lesson_ids=[])

    assert outcome == content_improvement_service.RunOutcome(0, 0, 0, 0)
    assert llm.prompts == []
    proposals.create.assert_not_awaited()


async def test_a_transient_provider_error_leaves_the_lesson_queued() -> None:
    # The 529 case. No proposal row of ANY status, so the lesson's feedback stays
    # uncovered and the next run picks it up -- no "Dismiss and retry later"
    # click needed. This is the whole point of the deferred count.
    lesson = _lesson()
    llm = _ScriptedLlm([_overloaded()])
    service, proposals, content = _service([(_feedback("a"), lesson)], llm=llm)

    outcome = await service.run(lesson_ids=[lesson.id])

    assert (outcome.proposed, outcome.skipped, outcome.deferred) == (0, 0, 1)
    proposals.create.assert_not_awaited()
    content.update_lesson.assert_not_awaited()


async def test_a_transient_error_on_one_lesson_does_not_abort_the_others() -> None:
    first, second = _lesson("First"), _lesson("Second")
    llm = _ScriptedLlm(
        [_overloaded(), {"proposed_blocks": _GOOD_BLOCKS, "summary": "Second one worked."}]
    )
    service, proposals, _content = _service(
        [(_feedback("a"), first), (_feedback("b"), second)], llm=llm
    )

    outcome = await service.run(lesson_ids=[first.id, second.id])

    assert (outcome.proposed, outcome.skipped, outcome.deferred) == (1, 0, 1)
    # Exactly one row: the success. The deferred lesson wrote nothing.
    assert proposals.create.await_count == 1
    assert proposals.create.await_args.kwargs["lesson_id"] == second.id


async def test_prompt_carries_the_lesson_and_every_feedback_message() -> None:
    lesson = _lesson()
    llm = _ScriptedLlm([{"proposed_blocks": _GOOD_BLOCKS, "summary": "s"}])
    service, _proposals, _content = _service(
        [(_feedback("too abstract"), lesson), (_feedback("add an example"), lesson)], llm=llm
    )

    await service.run(lesson_ids=[lesson.id])

    prompt = llm.prompts[0]
    assert "Prompting basics" in prompt
    assert "Old text." in prompt
    assert "too abstract" in prompt
    assert "add an example" in prompt
    assert "content" in llm.systems[0].lower()


async def test_system_prompt_composes_house_style_before_the_task_prompt() -> None:
    # _draft's system prompt must now be house_style.md FIRST, then
    # content_improvement.md, so the task prompt's "The house style above is
    # not background reading" reads as a continuation of real content.
    lesson = _lesson()
    llm = _ScriptedLlm([{"proposed_blocks": _GOOD_BLOCKS, "summary": "s"}])
    service, _proposals, _content = _service([(_feedback("a"), lesson)], llm=llm)

    await service.run(lesson_ids=[lesson.id])

    system = llm.systems[0]
    assert "Artefact" in system  # distinctive string from house_style.md
    assert "block by block diff" in system  # distinctive string from content_improvement.md
    assert system.index("Artefact") < system.index("block by block diff")


async def test_zero_approved_notes_leaves_the_prompt_byte_identical() -> None:
    # THE regression guard for this plan: nothing about drafting may change
    # just because the injection mechanism exists.
    expected = f"{load_prompt('house_style')}\n\n---\n\n{load_prompt('content_improvement')}"

    assert content_improvement_service._system_prompt([]) == expected


async def test_approved_notes_are_injected_between_house_style_and_the_task() -> None:
    composed = content_improvement_service._system_prompt(
        ["Prefer inline bullets over a card group."]
    )

    assert "Prefer inline bullets over a card group." in composed
    # House style first, notes in the middle, the task prompt last.
    assert composed.index("Artefact") < composed.index("Prefer inline bullets")
    assert composed.index("Prefer inline bullets") < composed.index("block by block diff")


async def test_the_notes_repository_is_read_once_per_run_not_once_per_lesson() -> None:
    first, lesson_a = _feedback("first"), _lesson("First")
    second, lesson_b = _feedback("second"), _lesson("Second")
    llm = _ScriptedLlm(
        [
            {"proposed_blocks": _GOOD_BLOCKS, "summary": "s"},
            {"proposed_blocks": _GOOD_BLOCKS, "summary": "s"},
        ]
    )
    notes = _notes_repo(["Prefer inline bullets over a card group."])
    service, _proposals, _content = _service(
        [(first, lesson_a), (second, lesson_b)], llm=llm, notes=notes
    )

    await service.run(lesson_ids=[lesson_a.id, lesson_b.id])

    assert len(llm.prompts) == 2
    # The limit is asserted, not just the call: hardcoding limit=1 here would
    # quietly starve the prompt of guidance and survive every other test.
    notes.list_for_injection.assert_awaited_once_with(limit=MAX_INJECTED_NOTES)
    # One read, but both drafting calls still carry the guidance.
    assert all("Prefer inline bullets over a card group." in system for system in llm.systems)


async def test_already_incorporated_feedback_is_not_redrafted() -> None:
    lesson = _lesson()
    done = _feedback("already covered")
    llm = _ScriptedLlm([])
    service, proposals, _content = _service([(done, lesson)], covered={done.id}, llm=llm)

    outcome = await service.run(lesson_ids=[lesson.id])

    # Covered feedback leaves the lesson out of the queue entirely, so asking
    # for it by id is a not_queued miss rather than a wasted model call.
    assert (outcome.proposed, outcome.not_queued) == (0, 1)
    assert llm.prompts == []
    proposals.create.assert_not_awaited()


async def test_invalid_blocks_are_never_stored_as_a_pending_proposal() -> None:
    lesson = _lesson()
    llm = _ScriptedLlm(
        [{"proposed_blocks": [{"id": "b1", "type": "banner", "text": "x"}], "summary": "s"}]
    )
    service, proposals, content = _service([(_feedback("a"), lesson)], llm=llm)

    outcome = await service.run(lesson_ids=[lesson.id])

    assert (outcome.proposed, outcome.skipped, outcome.deferred) == (0, 1, 0)
    content.update_lesson.assert_not_awaited()
    # Recorded as a `failed` proposal so this lesson stops re-consuming runs.
    assert proposals.create.await_args.kwargs["status"] == "failed"
    assert "banner" in proposals.create.await_args.kwargs["summary"]


async def test_a_card_missing_a_nested_id_is_repaired_not_rejected() -> None:
    # 66 of the 91 lessons in db/baseline/data/lessons.json have cards or quiz
    # questions with no `id`, and the agent is told to copy unchanged blocks
    # through verbatim -- so rejecting an id-less nested item would fail on most
    # of the real catalogue, forever. The draft path normalises instead, and
    # the minted ids are what gets STORED (approving heals the live lesson).
    lesson = _lesson()
    llm = _ScriptedLlm(
        [
            {
                "proposed_blocks": [
                    {
                        "id": "b1",
                        "type": "card_group",
                        "cards": [{"title": "No id here", "body": "x"}],
                    }
                ],
                "summary": "s",
            }
        ]
    )
    service, proposals, content = _service([(_feedback("a"), lesson)], llm=llm)

    outcome = await service.run(lesson_ids=[lesson.id])

    assert (outcome.proposed, outcome.skipped) == (1, 0)
    content.update_lesson.assert_not_awaited()
    kwargs = proposals.create.await_args.kwargs
    assert kwargs.get("status", "pending") == "pending"
    assert kwargs["proposed_blocks"][0]["cards"][0]["id"] == "b1-cards0"


async def test_duplicate_block_ids_are_still_rejected() -> None:
    # Normalisation repairs a MISSING id; it must not paper over two blocks
    # sharing one, which would collide in the learner renderer.
    lesson = _lesson()
    llm = _ScriptedLlm(
        [
            {
                "proposed_blocks": [
                    {"id": "b1", "type": "paragraph", "text": "First."},
                    {"id": "b1", "type": "paragraph", "text": "Second."},
                ],
                "summary": "s",
            }
        ]
    )
    service, proposals, content = _service([(_feedback("a"), lesson)], llm=llm)

    outcome = await service.run(lesson_ids=[lesson.id])

    assert (outcome.proposed, outcome.skipped) == (0, 1)
    content.update_lesson.assert_not_awaited()
    assert proposals.create.await_args.kwargs["status"] == "failed"
    assert "duplicate id" in proposals.create.await_args.kwargs["summary"]


async def test_a_new_media_locator_is_rejected() -> None:
    lesson = _lesson(blocks=[{"id": "b1", "type": "paragraph", "text": "Old text."}])
    invented = [
        {"id": "b1", "type": "paragraph", "text": "New text."},
        {"id": "b2", "type": "image", "blob_path": "images/made-up.png", "alt": "a chart"},
    ]
    llm = _ScriptedLlm([{"proposed_blocks": invented, "summary": "s"}])
    service, proposals, _content = _service([(_feedback("a"), lesson)], llm=llm)

    outcome = await service.run(lesson_ids=[lesson.id])

    assert (outcome.proposed, outcome.skipped) == (0, 1)
    assert proposals.create.await_args.kwargs["status"] == "failed"
    assert "made-up.png" in proposals.create.await_args.kwargs["summary"]


async def test_a_changed_block_with_an_em_dash_produces_a_failed_proposal_not_pending() -> None:
    # content_blocks_validation.check_house_style is wired into _draft, not
    # just structural/media validation -- a house-style violation in a block
    # the agent actually wrote must be refused the same way.
    lesson = _lesson(blocks=[{"id": "b1", "type": "paragraph", "text": "Old text."}])
    llm = _ScriptedLlm(
        [
            {
                "proposed_blocks": [
                    {"id": "b1", "type": "paragraph", "text": "New text — with an em dash."}
                ],
                "summary": "s",
            }
        ]
    )
    service, proposals, content = _service([(_feedback("a"), lesson)], llm=llm)

    outcome = await service.run(lesson_ids=[lesson.id])

    assert (outcome.proposed, outcome.skipped) == (0, 1)
    content.update_lesson.assert_not_awaited()
    kwargs = proposals.create.await_args.kwargs
    assert kwargs["status"] == "failed"
    assert "dash" in kwargs["summary"].lower()


async def test_an_empty_block_array_is_rejected() -> None:
    lesson = _lesson()
    llm = _ScriptedLlm([{"proposed_blocks": [], "summary": "wiped it"}])
    service, proposals, _content = _service([(_feedback("a"), lesson)], llm=llm)

    outcome = await service.run(lesson_ids=[lesson.id])

    assert (outcome.proposed, outcome.skipped) == (0, 1)
    assert proposals.create.await_args.kwargs["status"] == "failed"


async def test_an_unknown_model_error_is_recorded_and_does_not_abort_the_batch() -> None:
    # An unrecognised exception is TERMINAL, unlike the 529 above: re-queueing
    # on every unknown failure would let one poison lesson eat every run.
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

    outcome = await service.run(lesson_ids=[first.id, second.id])

    assert (outcome.proposed, outcome.skipped, outcome.deferred) == (1, 1, 0)
    assert proposals.create.await_count == 2


async def test_an_oversized_lesson_is_skipped_without_a_model_call() -> None:
    huge = _lesson(blocks=[{"id": "b1", "type": "paragraph", "text": "x" * 60_000}])
    llm = _ScriptedLlm([])
    service, proposals, _content = _service([(_feedback("a"), huge)], llm=llm)

    outcome = await service.run(lesson_ids=[huge.id])

    assert (outcome.proposed, outcome.skipped) == (0, 1)
    assert llm.prompts == []
    assert proposals.create.await_args.kwargs["status"] == "failed"
    assert "character" in proposals.create.await_args.kwargs["summary"]


async def test_a_hanging_call_times_out_and_counts_as_skipped() -> None:
    # A timeout is TERMINAL, not deferred: a lesson that always exceeds the
    # per-lesson budget would otherwise consume the whole run every time.
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
        _notes_repo(),
    )

    with mock.patch.object(content_improvement_service, "_PER_LESSON_TIMEOUT_SECONDS", 0.01):
        outcome = await service.run(lesson_ids=[lesson.id])

    assert (outcome.proposed, outcome.skipped, outcome.deferred) == (0, 1, 0)
    assert proposals.create.await_args.kwargs["status"] == "failed"


async def test_the_queue_lists_lessons_awaiting_a_draft_with_their_feedback_count() -> None:
    lesson = _lesson("Prompting basics")
    other = _lesson("Beyond chat")
    service, _proposals, content = _service(
        [
            (_feedback("too abstract"), lesson),
            (_feedback("add an example"), lesson),
            (_feedback("confusing"), other),
        ]
    )
    content.lesson_context.return_value = {
        lesson.id: ("Module A", uuid.uuid4(), "General I", "explore"),
        other.id: ("Module B", uuid.uuid4(), "General II", "practitioner"),
    }

    items = await service.list_queue()

    assert [item["lesson_title"] for item in items] == ["Prompting basics", "Beyond chat"]
    assert [item["feedback_count"] for item in items] == [2, 1]
    assert items[0]["module_title"] == "Module A"
    assert items[0]["track_name"] == "General I"
    assert items[0]["track_level"] == "explore"


async def test_a_queued_lesson_whose_track_is_missing_still_lists() -> None:
    # lesson_context is a separate read, so a lesson whose module/track row went
    # away between the two queries must not blank the whole picker.
    lesson = _lesson("Orphaned")
    service, _proposals, content = _service([(_feedback("a"), lesson)])
    content.lesson_context.return_value = {}

    items = await service.list_queue()

    assert len(items) == 1
    assert items[0]["lesson_title"] == "Orphaned"
    assert items[0]["feedback_count"] == 1


async def test_the_selected_lessons_are_drafted_concurrently_not_one_after_another() -> None:
    # A barrier is a real concurrency proof rather than a timing assertion: all
    # three calls must be in flight at once to get past it. Run sequentially,
    # the first call would wait for parties that never arrive and this test
    # would hang until its timeout -- which is exactly the bug it guards.
    lessons = [_lesson("First"), _lesson("Second"), _lesson("Third")]
    barrier = asyncio.Barrier(len(lessons))

    class _BarrierLlm:
        def __init__(self) -> None:
            self.calls = 0

        async def complete_structured(
            self, *, system: str, prompt: str, schema: object, max_tokens: int
        ) -> tuple[dict[str, Any], LlmUsage]:
            self.calls += 1
            async with asyncio.timeout(5):
                await barrier.wait()
            return (
                {"proposed_blocks": _GOOD_BLOCKS, "summary": "s"},
                LlmUsage(input_tokens=1, output_tokens=1),
            )

    llm = _BarrierLlm()
    service, proposals, _content = _service(
        [(_feedback(f"f{i}"), lesson) for i, lesson in enumerate(lessons)],
        llm=llm,  # ty: ignore[invalid-argument-type]
    )

    outcome = await service.run(lesson_ids=[lesson.id for lesson in lessons])

    assert outcome.proposed == 3
    assert llm.calls == 3
    assert proposals.create.await_count == 3


async def test_every_selected_lesson_is_attempted_even_when_one_fails() -> None:
    # "Don't queue lessons silently": with the drafts concurrent there is no
    # run-budget check between them, so a slow or failing lesson can no longer
    # cause a later one to be skipped and reported as merely "remaining".
    first, bad, third = _lesson("First"), _lesson("Bad"), _lesson("Third")
    llm = _ScriptedLlm(
        [
            {"proposed_blocks": _GOOD_BLOCKS, "summary": "s"},
            RuntimeError("this one is broken"),
            {"proposed_blocks": _GOOD_BLOCKS, "summary": "s"},
        ]
    )
    service, proposals, _content = _service(
        [(_feedback("a"), first), (_feedback("b"), bad), (_feedback("c"), third)], llm=llm
    )

    outcome = await service.run(lesson_ids=[first.id, bad.id, third.id])

    assert (outcome.proposed, outcome.skipped, outcome.deferred) == (2, 1, 0)
    # All three attempted, so nothing is left unexplained.
    assert len(llm.prompts) == 3
    # 2 pending + 1 failed row.
    assert proposals.create.await_count == 3
    statuses = sorted(
        call.kwargs.get("status", "pending") for call in proposals.create.await_args_list
    )
    assert statuses == ["failed", "pending", "pending"]


async def test_a_transient_failure_among_concurrent_drafts_only_defers_its_own_lesson() -> None:
    first, busy, third = _lesson("First"), _lesson("Busy"), _lesson("Third")
    llm = _ScriptedLlm(
        [
            {"proposed_blocks": _GOOD_BLOCKS, "summary": "s"},
            _overloaded(),
            {"proposed_blocks": _GOOD_BLOCKS, "summary": "s"},
        ]
    )
    service, proposals, _content = _service(
        [(_feedback("a"), first), (_feedback("b"), busy), (_feedback("c"), third)], llm=llm
    )

    outcome = await service.run(lesson_ids=[first.id, busy.id, third.id])

    assert (outcome.proposed, outcome.skipped, outcome.deferred) == (2, 0, 1)
    # The deferred lesson wrote NO row, so it is still queued for a retry.
    assert proposals.create.await_count == 2


async def test_the_per_lesson_timeout_leaves_headroom_under_the_container_ingress_timeout() -> None:
    # The drafts run concurrently, so a run's wall clock is one lesson's timeout
    # plus the sequential proposal writes -- not the sum of all three. This pins
    # the relationship the raised timeout depends on: blow past the 240s Azure
    # Container Apps ingress default and the admin gets a 504 while the server
    # keeps working, which is the confusing failure this guards against.
    assert content_improvement_service._PER_LESSON_TIMEOUT_SECONDS <= 200
    assert not hasattr(content_improvement_service, "_RUN_BUDGET_SECONDS")
