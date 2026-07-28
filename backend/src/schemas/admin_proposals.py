from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

__all__ = [
    "ImprovementRunResponse",
    "ProposalDetailOut",
    "ProposalFeedbackOut",
    "ProposalListResponse",
    "ProposalReviewRequest",
    "ProposalReviewResponse",
    "ProposalSummaryOut",
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


class ProposalReviewRequest(BaseModel):
    decision: ReviewDecision
    # The blocks the admin actually wants applied, when they changed the draft
    # in the review pane. Omitted (or identical to the agent's draft) means
    # "accept exactly as drafted", which is also what tells the pipeline there
    # is nothing to learn from this one. Ignored entirely on a reject.
    edited_blocks: list[dict[str, Any]] | None = None


class ProposalReviewResponse(BaseModel):
    status: ProposalStatus


class ImprovementRunResponse(BaseModel):
    """`proposed` = drafts created; `skipped` = lessons the agent could not
    draft (each recorded as a `failed` proposal carrying the reason);
    `remaining` = lessons the bounded run did not reach."""

    proposed: int
    skipped: int
    remaining: int
