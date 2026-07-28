from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from typing import Any
from unittest import mock
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import (
    AbstractCalibrationNoteRepository,
    AbstractContentRepository,
    AbstractFeedbackRepository,
    AbstractProposalRepository,
)
from src.services import content_improvement_service
from src.services.content_improvement_service import ContentImprovementService
from src.services.exceptions import AiGenerationError, ConflictError, NotFoundError
from src.services.llm_service import LlmUsage

_PROPOSED = [{"id": "b1", "type": "paragraph", "text": "The agent's wording."}]
_EDITED = [{"id": "b1", "type": "paragraph", "text": "The admin's wording."}]
_GOOD = {
    "what_agent_got_wrong": "I reached for a card group where prose was clearer.",
    "what_admin_preferred": "A single short paragraph.",
    "calibration_notes": ["Prefer inline bullets over a card group."],
}


class _ScriptedLlm:
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
        return result, LlmUsage(input_tokens=500, output_tokens=200)


def _proposal(**overrides: Any) -> Any:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "lesson_id": uuid.uuid4(),
        "proposed_blocks": _PROPOSED,
        "edited_blocks": _EDITED,
        "base_blocks": [],
        "status": "approved",
        "critiqued_at": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _service(
    proposal: Any | None, llm: Any
) -> tuple[ContentImprovementService, AsyncMock, AsyncMock]:
    proposals = AsyncMock(spec=AbstractProposalRepository)
    proposals.get_by_id.return_value = proposal
    notes = AsyncMock(spec=AbstractCalibrationNoteRepository)
    notes.create_many.return_value = []
    service = ContentImprovementService(
        proposals,
        AsyncMock(spec=AbstractFeedbackRepository),
        AsyncMock(spec=AbstractContentRepository),
        llm,
        notes,
    )
    return service, proposals, notes


async def test_critique_stores_the_assessment_and_one_note_per_string() -> None:
    proposal = _proposal()
    llm = _ScriptedLlm([_GOOD])
    service, proposals, notes = _service(proposal, llm)

    await service.critique(proposal_id=proposal.id)

    proposals.set_critique.assert_awaited_once_with(
        proposal,
        agent_wrong=_GOOD["what_agent_got_wrong"],
        admin_preferred=_GOOD["what_admin_preferred"],
    )
    notes.create_many.assert_awaited_once_with(
        source_proposal_id=proposal.id, notes=_GOOD["calibration_notes"]
    )


async def test_the_prompt_carries_both_arrays() -> None:
    proposal = _proposal()
    llm = _ScriptedLlm([_GOOD])
    service, _proposals, _notes = _service(proposal, llm)

    await service.critique(proposal_id=proposal.id)

    prompt = llm.prompts[0]
    assert "The agent's wording." in prompt
    assert "The admin's wording." in prompt
    # The critique agent must NOT be given the house style — it writes no lesson content.
    assert "Artefact" not in llm.systems[0]


async def test_a_proposal_accepted_untouched_has_nothing_to_learn() -> None:
    proposal = _proposal(edited_blocks=None)
    service, proposals, notes = _service(proposal, _ScriptedLlm([]))

    with pytest.raises(ConflictError):
        await service.critique(proposal_id=proposal.id)

    proposals.set_critique.assert_not_awaited()
    notes.create_many.assert_not_awaited()


async def test_a_pending_proposal_is_refused() -> None:
    proposal = _proposal(status="pending")
    service, proposals, _notes = _service(proposal, _ScriptedLlm([]))

    with pytest.raises(ConflictError):
        await service.critique(proposal_id=proposal.id)

    proposals.set_critique.assert_not_awaited()


async def test_a_second_critique_is_refused_so_notes_are_never_duplicated() -> None:
    proposal = _proposal(critiqued_at="2026-07-28T00:00:00Z")
    service, _proposals, notes = _service(proposal, _ScriptedLlm([]))

    with pytest.raises(ConflictError):
        await service.critique(proposal_id=proposal.id)

    notes.create_many.assert_not_awaited()


async def test_unknown_proposal_raises_not_found() -> None:
    service, _proposals, _notes = _service(None, _ScriptedLlm([]))

    with pytest.raises(NotFoundError):
        await service.critique(proposal_id=uuid.uuid4())


async def test_a_model_error_becomes_an_ai_generation_error() -> None:
    proposal = _proposal()
    service, proposals, _notes = _service(
        proposal, _ScriptedLlm([RuntimeError("Anthropic API unreachable")])
    )

    with pytest.raises(AiGenerationError):
        await service.critique(proposal_id=proposal.id)

    proposals.set_critique.assert_not_awaited()


async def test_unusable_output_becomes_an_ai_generation_error() -> None:
    proposal = _proposal()
    service, proposals, _notes = _service(
        proposal,
        _ScriptedLlm(
            [{"what_agent_got_wrong": "", "what_admin_preferred": "x", "calibration_notes": ["y"]}]
        ),
    )

    with pytest.raises(AiGenerationError):
        await service.critique(proposal_id=proposal.id)

    proposals.set_critique.assert_not_awaited()


async def test_an_oversized_array_on_either_side_is_refused() -> None:
    huge = [{"id": "b1", "type": "paragraph", "text": "x" * 60_000}]
    for field in ("proposed_blocks", "edited_blocks"):
        proposal = _proposal(**{field: huge})
        llm = _ScriptedLlm([])
        service, _proposals, _notes = _service(proposal, llm)

        with pytest.raises(AiGenerationError):
            await service.critique(proposal_id=proposal.id)

        assert llm.prompts == []


async def test_a_hanging_call_times_out() -> None:
    proposal = _proposal()

    class _Hanging:
        async def complete_structured(self, **_: object) -> tuple[dict[str, Any], LlmUsage]:
            await asyncio.sleep(3600)
            raise AssertionError("unreachable")

    service, proposals, _notes = _service(proposal, _Hanging())

    with (
        mock.patch.object(content_improvement_service, "_CRITIQUE_TIMEOUT_SECONDS", 0.01),
        pytest.raises(AiGenerationError),
    ):
        await service.critique(proposal_id=proposal.id)

    proposals.set_critique.assert_not_awaited()
