from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import (
    AbstractCalibrationNoteRepository,
    AbstractContentRepository,
    AbstractFeedbackRepository,
    AbstractProposalRepository,
)
from src.services.content_improvement_service import ContentImprovementService
from src.services.exceptions import ConflictError, InvalidRequestError, NotFoundError

_BASE = [{"id": "b1", "type": "paragraph", "text": "Old text."}]
_PROPOSED = [
    {"id": "b1", "type": "paragraph", "text": "New, clearer text."},
    {"id": "b2", "type": "paragraph", "text": "With an example."},
]


def _proposal(**overrides: Any) -> Any:
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "lesson_id": uuid.uuid4(),
        "proposed_blocks": _PROPOSED,
        "base_blocks": _BASE,
        "source_feedback_ids": [str(uuid.uuid4())],
        "summary": "Reworded and added an example.",
        "status": "pending",
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _lesson(blocks: list[Any]) -> Any:
    return SimpleNamespace(id=uuid.uuid4(), title="Prompting basics", content_blocks=blocks)


def _service(
    proposal: Any | None, lesson: Any | None
) -> tuple[ContentImprovementService, AsyncMock, AsyncMock]:
    proposals = AsyncMock(spec=AbstractProposalRepository)
    proposals.get_by_id.return_value = proposal
    content = AsyncMock(spec=AbstractContentRepository)
    content.get_lesson.return_value = lesson
    service = ContentImprovementService(
        proposals,
        AsyncMock(spec=AbstractFeedbackRepository),
        content,
        AsyncMock(),
        AsyncMock(spec=AbstractCalibrationNoteRepository),
    )
    return service, proposals, content


async def test_approve_writes_the_lesson_and_stamps_the_proposal() -> None:
    proposal = _proposal()
    lesson = _lesson(list(_BASE))
    service, proposals, content = _service(proposal, lesson)
    reviewer_id = uuid.uuid4()

    result = await service.review(
        proposal_id=proposal.id, decision="approve", reviewer_id=reviewer_id
    )

    assert result == "approved"
    content.update_lesson.assert_awaited_once_with(lesson, {"content_blocks": _PROPOSED})
    proposals.set_approved.assert_awaited_once_with(
        proposal, edited_blocks=None, reviewed_by=reviewer_id
    )


async def test_approve_strips_an_ephemeral_media_url_before_writing() -> None:
    stamped = [
        {
            "id": "m1",
            "type": "image",
            "blob_path": "images/a.png",
            "alt": "a chart",
            "url": "https://blob.test/images/a.png?sig=abc",
        }
    ]
    proposal = _proposal(base_blocks=stamped, proposed_blocks=stamped)
    lesson = _lesson(list(stamped))
    service, _proposals, content = _service(proposal, lesson)

    await service.review(proposal_id=proposal.id, decision="approve", reviewer_id=uuid.uuid4())

    written = content.update_lesson.await_args.args[1]["content_blocks"]
    assert "url" not in written[0]
    assert written[0]["blob_path"] == "images/a.png"


async def test_reject_discards_without_touching_the_lesson() -> None:
    proposal = _proposal()
    service, proposals, content = _service(proposal, _lesson(list(_BASE)))
    reviewer_id = uuid.uuid4()

    result = await service.review(
        proposal_id=proposal.id, decision="reject", reviewer_id=reviewer_id
    )

    assert result == "rejected"
    content.update_lesson.assert_not_awaited()
    proposals.set_status.assert_awaited_once_with(proposal, "rejected", reviewer_id)


async def test_a_lesson_that_moved_supersedes_the_proposal_and_refuses() -> None:
    proposal = _proposal()
    moved = _lesson([{"id": "b1", "type": "paragraph", "text": "An admin edited this."}])
    service, proposals, content = _service(proposal, moved)
    reviewer_id = uuid.uuid4()

    with pytest.raises(ConflictError):
        await service.review(proposal_id=proposal.id, decision="approve", reviewer_id=reviewer_id)

    content.update_lesson.assert_not_awaited()
    proposals.set_status.assert_awaited_once_with(proposal, "superseded", reviewer_id)


async def test_blocks_that_no_longer_validate_are_refused_at_apply_time() -> None:
    proposal = _proposal(proposed_blocks=[{"id": "b1", "type": "banner", "text": "x"}])
    service, proposals, content = _service(proposal, _lesson(list(_BASE)))

    with pytest.raises(ConflictError):
        await service.review(proposal_id=proposal.id, decision="approve", reviewer_id=uuid.uuid4())

    content.update_lesson.assert_not_awaited()
    proposals.set_status.assert_not_awaited()


async def test_a_media_locator_snuck_in_is_refused_at_apply_time() -> None:
    proposal = _proposal(
        proposed_blocks=[
            {"id": "b1", "type": "image", "blob_path": "images/made-up.png", "alt": "x"}
        ]
    )
    service, _proposals, content = _service(proposal, _lesson(list(_BASE)))

    with pytest.raises(ConflictError):
        await service.review(proposal_id=proposal.id, decision="approve", reviewer_id=uuid.uuid4())

    content.update_lesson.assert_not_awaited()


async def test_an_already_reviewed_proposal_is_refused() -> None:
    proposal = _proposal(status="approved")
    service, _proposals, content = _service(proposal, _lesson(list(_BASE)))

    with pytest.raises(ConflictError):
        await service.review(proposal_id=proposal.id, decision="approve", reviewer_id=uuid.uuid4())

    content.update_lesson.assert_not_awaited()


@pytest.mark.parametrize("status", ["rejected", "superseded"])
async def test_a_decided_proposal_is_refused_regardless_of_which_decision(status: str) -> None:
    proposal = _proposal(status=status)
    service, _proposals, content = _service(proposal, _lesson(list(_BASE)))

    with pytest.raises(ConflictError):
        await service.review(proposal_id=proposal.id, decision="approve", reviewer_id=uuid.uuid4())
    with pytest.raises(ConflictError):
        await service.review(proposal_id=proposal.id, decision="reject", reviewer_id=uuid.uuid4())

    content.update_lesson.assert_not_awaited()


async def test_a_failed_proposal_can_be_rejected_but_not_approved() -> None:
    proposal = _proposal(status="failed", proposed_blocks=[])
    service, proposals, content = _service(proposal, _lesson(list(_BASE)))

    with pytest.raises(ConflictError):
        await service.review(proposal_id=proposal.id, decision="approve", reviewer_id=uuid.uuid4())
    content.update_lesson.assert_not_awaited()

    reviewer_id = uuid.uuid4()
    assert (
        await service.review(proposal_id=proposal.id, decision="reject", reviewer_id=reviewer_id)
        == "rejected"
    )
    proposals.set_status.assert_awaited_once_with(proposal, "rejected", reviewer_id)


async def test_unknown_proposal_and_deleted_lesson_raise_not_found() -> None:
    service, _proposals, _content = _service(None, None)
    with pytest.raises(NotFoundError):
        await service.review(proposal_id=uuid.uuid4(), decision="approve", reviewer_id=uuid.uuid4())

    proposal = _proposal()
    service, _proposals, _content = _service(proposal, None)
    with pytest.raises(NotFoundError):
        await service.review(proposal_id=proposal.id, decision="approve", reviewer_id=uuid.uuid4())


async def test_an_unknown_decision_never_applies_anything() -> None:
    proposal = _proposal()
    service, proposals, content = _service(proposal, _lesson(list(_BASE)))

    for decision in ("", "APPROVE", "publish"):
        with pytest.raises(InvalidRequestError):
            await service.review(
                proposal_id=proposal.id, decision=decision, reviewer_id=uuid.uuid4()
            )

    content.update_lesson.assert_not_awaited()
    proposals.set_status.assert_not_awaited()


_ADMIN_EDITED = [
    {"id": "b1", "type": "paragraph", "text": "The admin's own wording."},
]


async def test_approving_without_edits_is_unchanged_behaviour() -> None:
    # THE regression guard for this whole plan: the no-edits path must keep
    # applying the agent's array and must leave edited_blocks NULL.
    proposal = _proposal()
    lesson = _lesson(list(_BASE))
    service, proposals, content = _service(proposal, lesson)
    reviewer_id = uuid.uuid4()

    assert (
        await service.review(proposal_id=proposal.id, decision="approve", reviewer_id=reviewer_id)
        == "approved"
    )

    content.update_lesson.assert_awaited_once_with(lesson, {"content_blocks": _PROPOSED})
    proposals.set_approved.assert_awaited_once_with(
        proposal, edited_blocks=None, reviewed_by=reviewer_id
    )


async def test_edits_identical_to_the_draft_count_as_unchanged() -> None:
    proposal = _proposal()
    service, proposals, content = _service(proposal, _lesson(list(_BASE)))

    await service.review(
        proposal_id=proposal.id,
        decision="approve",
        reviewer_id=uuid.uuid4(),
        edited_blocks=list(_PROPOSED),
    )

    content.update_lesson.assert_awaited_once()
    assert proposals.set_approved.await_args.kwargs["edited_blocks"] is None


async def test_edits_apply_the_admin_array_and_store_the_delta() -> None:
    proposal = _proposal()
    lesson = _lesson(list(_BASE))
    service, proposals, content = _service(proposal, lesson)
    reviewer_id = uuid.uuid4()

    await service.review(
        proposal_id=proposal.id,
        decision="approve",
        reviewer_id=reviewer_id,
        edited_blocks=list(_ADMIN_EDITED),
    )

    # The ADMIN's text reaches the lesson, not the agent's.
    content.update_lesson.assert_awaited_once_with(lesson, {"content_blocks": _ADMIN_EDITED})
    proposals.set_approved.assert_awaited_once_with(
        proposal, edited_blocks=_ADMIN_EDITED, reviewed_by=reviewer_id
    )


async def test_admin_edits_are_structurally_validated() -> None:
    proposal = _proposal()
    service, proposals, content = _service(proposal, _lesson(list(_BASE)))

    with pytest.raises(ConflictError):
        await service.review(
            proposal_id=proposal.id,
            decision="approve",
            reviewer_id=uuid.uuid4(),
            edited_blocks=[{"id": "b1", "type": "banner", "text": "x"}],
        )

    content.update_lesson.assert_not_awaited()
    proposals.set_approved.assert_not_awaited()


async def test_admin_edits_cannot_invent_a_media_locator() -> None:
    proposal = _proposal()
    service, _proposals, content = _service(proposal, _lesson(list(_BASE)))

    with pytest.raises(ConflictError):
        await service.review(
            proposal_id=proposal.id,
            decision="approve",
            reviewer_id=uuid.uuid4(),
            edited_blocks=[
                {"id": "b1", "type": "image", "blob_path": "images/made-up.png", "alt": "x"}
            ],
        )

    content.update_lesson.assert_not_awaited()


async def test_admin_edits_are_NOT_house_style_checked() -> None:
    # House style is a rule for the AGENT, derived from this person's own
    # writing. An em dash in the admin's own paragraph must be accepted.
    proposal = _proposal()
    lesson = _lesson(list(_BASE))
    service, _proposals, content = _service(proposal, lesson)

    await service.review(
        proposal_id=proposal.id,
        decision="approve",
        reviewer_id=uuid.uuid4(),
        edited_blocks=[
            {"id": "b1", "type": "paragraph", "text": "Written by a human — with a dash."}
        ],
    )

    content.update_lesson.assert_awaited_once()


async def test_an_unchanged_agent_draft_is_still_house_style_checked() -> None:
    # Mirror of test_admin_edits_are_NOT_house_style_checked: the same rule
    # that exempts an admin's own prose must still gate the agent's, when the
    # admin approves the draft with no edits at all.
    proposal = _proposal(
        proposed_blocks=[{"id": "b1", "type": "paragraph", "text": "Look at this — closely."}]
    )
    service, proposals, content = _service(proposal, _lesson(list(_BASE)))

    with pytest.raises(ConflictError):
        await service.review(proposal_id=proposal.id, decision="approve", reviewer_id=uuid.uuid4())

    content.update_lesson.assert_not_awaited()
    proposals.set_approved.assert_not_awaited()


async def test_edits_missing_only_nested_ids_normalise_to_the_same_draft() -> None:
    # The MDX editor round-trip can drop a nested id (this module's own
    # docstring calls that out). If normalising the admin's submission
    # reconstructs exactly the agent's array, that is still "unchanged": no
    # delta should be stored and no learn card produced for nothing.
    proposed = [
        {
            "id": "b1",
            "type": "card_group",
            "cards": [{"id": "b1-cards0", "title": "A card", "body": "Some body text."}],
        }
    ]
    proposal = _proposal(proposed_blocks=proposed)
    lesson = _lesson(list(_BASE))
    service, proposals, content = _service(proposal, lesson)
    reviewer_id = uuid.uuid4()
    edited_blocks = [
        {
            "id": "b1",
            "type": "card_group",
            # Same card, minus its nested id.
            "cards": [{"title": "A card", "body": "Some body text."}],
        }
    ]

    await service.review(
        proposal_id=proposal.id,
        decision="approve",
        reviewer_id=reviewer_id,
        edited_blocks=edited_blocks,
    )

    content.update_lesson.assert_awaited_once_with(lesson, {"content_blocks": proposed})
    proposals.set_approved.assert_awaited_once_with(
        proposal, edited_blocks=None, reviewed_by=reviewer_id
    )


async def test_a_stale_base_still_supersedes_even_with_edits() -> None:
    proposal = _proposal()
    moved = _lesson([{"id": "b1", "type": "paragraph", "text": "Someone else edited this."}])
    service, proposals, content = _service(proposal, moved)
    reviewer_id = uuid.uuid4()

    with pytest.raises(ConflictError):
        await service.review(
            proposal_id=proposal.id,
            decision="approve",
            reviewer_id=reviewer_id,
            edited_blocks=list(_ADMIN_EDITED),
        )

    content.update_lesson.assert_not_awaited()
    proposals.set_status.assert_awaited_once_with(proposal, "superseded", reviewer_id)


async def test_edited_blocks_are_ignored_on_reject() -> None:
    proposal = _proposal()
    service, proposals, content = _service(proposal, _lesson(list(_BASE)))
    reviewer_id = uuid.uuid4()

    assert (
        await service.review(
            proposal_id=proposal.id,
            decision="reject",
            reviewer_id=reviewer_id,
            edited_blocks=list(_ADMIN_EDITED),
        )
        == "rejected"
    )

    content.update_lesson.assert_not_awaited()
    proposals.set_status.assert_awaited_once_with(proposal, "rejected", reviewer_id)
