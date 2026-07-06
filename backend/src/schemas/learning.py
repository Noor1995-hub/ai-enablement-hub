from __future__ import annotations

import uuid
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


class ModuleNode(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    title: str
    sort_order: int
    assigned: bool
    lesson_count: int
    completed_lesson_count: int


class PrerequisiteEdge(BaseModel):
    module_id: uuid.UUID
    prerequisite_module_id: uuid.UUID


class LearningGraphResponse(BaseModel):
    tracks: list[TrackNode]
    modules: list[ModuleNode]
    prerequisites: list[PrerequisiteEdge]


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
    next_module_id: uuid.UUID | None


class LessonProgressRequest(BaseModel):
    answers: dict[str, Any] | None = None
