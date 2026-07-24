from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from src.core.dependencies.auth import require_admin
from src.core.dependencies.domain import get_feedback_service
from src.db.models import User
from src.schemas.admin_feedback import (
    AdminFeedbackListResponse,
    AdminFeedbackOut,
    FeedbackStatusUpdateRequest,
)
from src.services.feedback_service import FeedbackService

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin", tags=["admin:feedback"], dependencies=[Depends(require_admin)]
)

FeedbackServiceDep = Annotated[FeedbackService, Depends(get_feedback_service)]


@router.get("/feedback", response_model=AdminFeedbackListResponse)
async def list_feedback(
    feedback_service: FeedbackServiceDep,
    status_filter: Annotated[
        Literal["new", "accepted", "dismissed"] | None, Query(alias="status")
    ] = None,
    track_id: Annotated[uuid.UUID | None, Query()] = None,
    project_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminFeedbackListResponse:
    items, total = await feedback_service.list_admin(
        status=status_filter, track_id=track_id, project_id=project_id, limit=limit, offset=offset
    )
    return AdminFeedbackListResponse(
        items=[AdminFeedbackOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/feedback/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def set_feedback_status(
    feedback_id: uuid.UUID,
    body: FeedbackStatusUpdateRequest,
    feedback_service: FeedbackServiceDep,
    admin: Annotated[User, Depends(require_admin)],
) -> None:
    await feedback_service.set_status(feedback_id, body.status, admin.id)
