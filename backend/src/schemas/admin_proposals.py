from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

__all__ = [
    "MAX_LESSONS_PER_RUN",
    "CalibrationNoteBrief",
    "ImprovementRunRequest",
    "ImprovementRunResponse",
    "LearnCardOut",
    "ProposalDetailOut",
    "ProposalFeedbackOut",
    "ProposalListResponse",
    "ProposalReviewRequest",
    "ProposalReviewResponse",
    "ProposalSummaryOut",
    "QueueItemOut",
    "QueueResponse",
]

# 'failed' means the agent could not draft a revision for that lesson; the row
# exists so the lesson stops re-consuming every run and the admin can see why.
ProposalStatus = Literal["pending", "approved", "rejected", "superseded", "failed"]
ReviewDecision = Literal["approve", "reject"]


class ProposalSummaryOut(BaseModel):
    """One row of the review queue — no block arrays (see ProposalDetailOut)."""

    id: uuid.UUID
    lesson_id: uuid.UUID
    lesson_title: str
    module_title: str
    track_id: uuid.UUID
    track_name: str
    track_level: str
    summary: str
    status: ProposalStatus
    source_feedback_count: int
    created_at: datetime
    reviewed_at: datetime | None


class ProposalListResponse(BaseModel):
    items: list[ProposalSummaryOut]
    total: int
    limit: int
    offset: int


class ProposalFeedbackOut(BaseModel):
    id: uuid.UUID
    message: str
    created_at: datetime


class CalibrationNoteBrief(BaseModel):
    id: uuid.UUID
    note: str
    status: str


class LearnCardOut(BaseModel):
    """What the agent concluded from comparing its draft to the accepted version.
    `calibration_notes` are SUGGESTIONS — they influence nothing until an admin
    approves them."""

    critique_agent_wrong: str
    critique_admin_preferred: str
    critiqued_at: datetime
    calibration_notes: list[CalibrationNoteBrief]


class ProposalDetailOut(BaseModel):
    """Everything the diff view needs. `base_blocks`/`proposed_blocks` are the
    opaque content_blocks arrays; the frontend renders them as PLAIN TEXT —
    they are model output."""

    id: uuid.UUID
    lesson_id: uuid.UUID
    lesson_title: str
    summary: str
    status: ProposalStatus
    base_blocks: list[Any]
    proposed_blocks: list[Any]
    source_feedback: list[ProposalFeedbackOut]
    created_at: datetime
    reviewed_at: datetime | None
    edited_blocks: list[Any] | None = None
    critique_agent_wrong: str | None = None
    critique_admin_preferred: str | None = None
    critiqued_at: datetime | None = None
    calibration_notes: list[CalibrationNoteBrief] = Field(default_factory=list)


class ProposalReviewRequest(BaseModel):
    decision: ReviewDecision
    # The blocks the admin actually wants applied, when they changed the draft
    # in the review pane. Omitted (or identical to the agent's draft) means
    # "accept exactly as drafted", which is also what tells the pipeline there
    # is nothing to learn from this one. Ignored entirely on a reject.
    edited_blocks: list[dict[str, Any]] | None = None


class ProposalReviewResponse(BaseModel):
    status: ProposalStatus


# One click fans out to this many whole-lesson rewrites at most. The ceiling is
# concurrency against the container ingress timeout, not the model: the drafts
# run in parallel, so raising this raises the peak load on the Anthropic key (and
# the burn rate) rather than the wall clock. See _PER_LESSON_TIMEOUT_SECONDS in
# services/content_improvement_service.py.
MAX_LESSONS_PER_RUN = 3


class ImprovementRunRequest(BaseModel):
    """The lessons the admin picked out of the queue. Explicit on purpose — a
    run that chose for itself would spend money on lessons nobody asked about."""

    lesson_ids: list[uuid.UUID] = Field(min_length=1, max_length=MAX_LESSONS_PER_RUN)


class ImprovementRunResponse(BaseModel):
    """`proposed` = drafts created; `skipped` = lessons the agent could not
    draft (each recorded as a `failed` proposal carrying the reason);
    `deferred` = lessons the AI provider was too busy for, still queued and
    retried by the next run; `not_queued` = requested lessons that were already
    drafted by a concurrent run.

    There is deliberately no "did not get to it" count: the drafts run
    concurrently, so every selected lesson is always attempted and lands in
    exactly one of the three buckets above."""

    proposed: int
    skipped: int
    deferred: int
    not_queued: int


class QueueItemOut(BaseModel):
    """One lesson awaiting a draft. `track_id` is nullable because the queue's
    module/track labels come from a second read — a lesson whose track row went
    away still needs to be pickable."""

    lesson_id: uuid.UUID
    lesson_title: str
    module_title: str
    track_id: uuid.UUID | None
    track_name: str
    track_level: str
    feedback_count: int


class QueueResponse(BaseModel):
    items: list[QueueItemOut]
    total: int
