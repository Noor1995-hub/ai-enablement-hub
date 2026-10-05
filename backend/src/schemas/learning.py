from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

__all__ = [
    "LearningGraphResponse",
    "LessonDetailResponse",
    "LessonModuleInfo",
    "LessonProgressRequest",
    "ModuleLessonItem",
    "ModuleLessonsResponse",
    "ModuleNode",
    "PrerequisiteEdge",
    "TrackNode",
]


class TrackNode(BaseModel):
    id: uuid.UUID
    name: str
    sort_order: int
    track_type: str
    color: str | None
    assigned: bool
    required_level: str
    # False when the caller's effective maturity is below required_level (or
    # they have no maturity at all). Admins bypass this client-side.
    unlocked_by_maturity: bool
    # True for the mandatory pre-Explorer Introduction track. Drives the client's
    # separate "Introduction" group + completion gate; absent from LEVELS.
    is_introduction: bool


class ModuleNode(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    title: str
    sort_order: int
    assigned: bool
    lesson_count: int
    completed_lesson_count: int
    # Inherited from the module's track — a module in a maturity-locked track is
    # locked by inheritance (prerequisites still gate within an unlocked track).
    unlocked_by_maturity: bool
    # Inherited from the module's track (a module of the Introduction track).
    is_introduction: bool


class PrerequisiteEdge(BaseModel):
    module_id: uuid.UUID
    prerequisite_module_id: uuid.UUID


class LearningGraphResponse(BaseModel):
    tracks: list[TrackNode]
    modules: list[ModuleNode]
    prerequisites: list[PrerequisiteEdge]
    # The caller's effective maturity (override- and progression-aware), or null
    # when they have no maturity yet. Drives the page's level header.
    maturity_level: str | None


class ModuleLessonItem(BaseModel):
    id: uuid.UUID
    title: str
    sort_order: int
    completed: bool
    assigned: bool


class ModuleLessonsResponse(BaseModel):
    lessons: list[ModuleLessonItem]
    next_lesson_id: uuid.UUID | None


class LessonModuleInfo(BaseModel):
    id: uuid.UUID
    title: str
    track_id: uuid.UUID
    sort_order: int


class LessonDetailResponse(BaseModel):
    id: uuid.UUID
    module_id: uuid.UUID
    title: str
    sort_order: int
    content_blocks: list[Any]
    module: LessonModuleInfo
    my_answers: dict[str, Any] | None
    next_lesson_id: uuid.UUID | None
    # B5: the editor's conflict-check base (echoed back as expected_updated_at).
    updated_at: datetime
    next_module_id: uuid.UUID | None


class LessonProgressRequest(BaseModel):
    answers: dict[str, Any] | None = None
