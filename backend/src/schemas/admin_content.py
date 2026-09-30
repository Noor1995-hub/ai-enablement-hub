from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.schemas._validators import require_non_blank

__all__ = [
    "LessonCreateRequest",
    "LessonOrderRequest",
    "LessonOut",
    "LessonSummaryOut",
    "LessonUpdateRequest",
    "ModuleCreateRequest",
    "ModuleOut",
    "TrackCreateRequest",
    "TrackModuleOut",
    "TrackOut",
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

    _non_blank = field_validator("title")(require_non_blank)


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: uuid.UUID
    title: str
    sort_order: int
    content_blocks: list[Any]


class LessonOrderRequest(BaseModel):
    lesson_ids: list[uuid.UUID]
