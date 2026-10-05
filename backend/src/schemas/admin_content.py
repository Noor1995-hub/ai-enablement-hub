from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.schemas._validators import require_non_blank

__all__ = [
    "AssignGapResponse",
    "AssignmentGapResponse",
    "ContentTreeResponse",
    "DeleteImpactResponse",
    "LessonCheckRequest",
    "LessonCheckResponse",
    "LessonCreateRequest",
    "LessonFindingOut",
    "LessonOrderRequest",
    "LessonOut",
    "LessonSummaryOut",
    "LessonUpdateRequest",
    "ModuleCreateRequest",
    "ModuleOrderRequest",
    "ModuleOut",
    "ModuleUpdateRequest",
    "PrerequisitesRequest",
    "TrackCreateRequest",
    "TrackModuleOut",
    "TrackOrderRequest",
    "TrackOut",
    "TrackUpdateRequest",
    "TreeLesson",
    "TreeModule",
    "TreeTrack",
]


class TrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    sort_order: int
    track_type: str
    color: str | None
    required_level: str
    is_introduction: bool


class TrackModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    sort_order: int


class TrackCreateRequest(BaseModel):
    name: str
    track_type: Literal["tool", "general"]
    color: str | None = None

    _non_blank = field_validator("name")(require_non_blank)


class ModuleCreateRequest(BaseModel):
    track_id: uuid.UUID
    title: str
    after_module_id: uuid.UUID | None = None
    prerequisite_ids: list[uuid.UUID] = Field(default_factory=list)

    _non_blank = field_validator("title")(require_non_blank)


class ModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    track_id: uuid.UUID
    title: str
    sort_order: int
    description: str | None = None


class LessonCreateRequest(BaseModel):
    module_id: uuid.UUID
    title: str

    _non_blank = field_validator("title")(require_non_blank)


class LessonSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    sort_order: int


class LessonUpdateRequest(BaseModel):
    title: str | None = None
    content_blocks: list[dict[str, Any]] | None = None
    # B4: a different module moves the lesson to the end of that module.
    module_id: uuid.UUID | None = None
    # B5: the updated_at the editor loaded. A mismatch → 409 lesson_changed.
    # Optional for one release (the deployed frontend doesn't send it yet).
    expected_updated_at: datetime | None = None

    _non_blank = field_validator("title")(require_non_blank)


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: uuid.UUID
    title: str
    sort_order: int
    content_blocks: list[Any]
    updated_at: datetime


class LessonOrderRequest(BaseModel):
    lesson_ids: list[uuid.UUID]


Level = Literal["explore", "practitioner", "integrator", "multiplier"]


def _not_null(value: object) -> object:
    """An omitted field never reaches a validator; an explicit null does. These
    columns are NOT NULL, so null is refused here (422) instead of failing in
    the service or the database."""
    if value is None:
        msg = "must not be null"
        raise ValueError(msg)
    return value


class TrackUpdateRequest(BaseModel):
    """All optional; only `color` may be set to null (no colour)."""

    name: str | None = None
    color: str | None = None
    track_type: Literal["tool", "general"] | None = None
    required_level: Level | None = None

    _non_blank = field_validator("name")(require_non_blank)
    _not_null = field_validator("name", "track_type", "required_level")(_not_null)


class TrackOrderRequest(BaseModel):
    track_ids: list[uuid.UUID]


class ModuleUpdateRequest(BaseModel):
    """All optional; `description` may be null. A different `track_id` moves
    the module to the end of that track."""

    title: str | None = None
    description: str | None = None
    track_id: uuid.UUID | None = None

    _non_blank = field_validator("title")(require_non_blank)
    _not_null = field_validator("title", "track_id")(_not_null)


class ModuleOrderRequest(BaseModel):
    module_ids: list[uuid.UUID]


class PrerequisitesRequest(BaseModel):
    prerequisite_ids: list[uuid.UUID]


class TreeLesson(BaseModel):
    id: uuid.UUID
    title: str
    sort_order: int


class TreeModule(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    sort_order: int
    prerequisite_ids: list[uuid.UUID]
    lesson_count: int
    lessons: list[TreeLesson]


class TreeTrack(BaseModel):
    id: uuid.UUID
    name: str
    color: str | None
    track_type: str
    required_level: str
    is_introduction: bool
    sort_order: int
    modules: list[TreeModule]


class ContentTreeResponse(BaseModel):
    tracks: list[TreeTrack]


class DeleteImpactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    modules: int
    lessons: int
    learners_assigned: int
    learners_with_progress: int


class AssignmentGapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lesson_ids: list[uuid.UUID]
    learner_count: int
    missing_pairs: int


class AssignGapResponse(BaseModel):
    assigned_pairs: int


class LessonCheckRequest(BaseModel):
    """The editor's UNSAVED blocks (B5)."""

    content_blocks: list[dict[str, Any]]


class LessonFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    severity: Literal["warning", "info"]
    block_index: int | None
    where: str
    message: str


class LessonCheckResponse(BaseModel):
    findings: list[LessonFindingOut]
