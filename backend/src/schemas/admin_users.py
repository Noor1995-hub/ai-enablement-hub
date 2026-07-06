from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

__all__ = [
    "AdminLearningLessonOut",
    "AdminLearningModuleOut",
    "AdminLearningResponse",
    "AdminLearningUserOut",
    "AdminSurveyOut",
    "AdminUserOut",
    "AdminUsersResponse",
    "AssignmentRequest",
    "BulkLessonAssignmentRequest",
    "BulkModuleAssignmentRequest",
    "BulkTrackAssignmentRequest",
    "EmailStatus",
    "InviteRequest",
    "LinkResponse",
    "RoleUpdateRequest",
    "SurveyLevelsResponse",
    "UserSurveyResponse",
]


def _require_non_blank(value: str) -> str:
    if not value.strip():
        msg = "must not be blank"
        raise ValueError(msg)
    return value


class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    password_set: bool
    created_at: datetime
    company_id: uuid.UUID | None
    project_id: uuid.UUID | None
    company_name: str | None
    project_name: str | None
    assigned_track_ids: list[uuid.UUID]
    assigned_module_ids: list[uuid.UUID]
    assigned_lesson_ids: list[uuid.UUID]


class AdminUsersResponse(BaseModel):
    users: list[AdminUserOut]


class InviteRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    project_id: uuid.UUID

    _non_blank = field_validator("first_name", "last_name")(_require_non_blank)


# "sent" = ACS accepted the message; "failed" = send errored (admin shares the
# link manually); "disabled" = EMAIL__* unconfigured.
EmailStatus = Literal["sent", "failed", "disabled"]


class LinkResponse(BaseModel):
    link: str
    email_status: EmailStatus


class RoleUpdateRequest(BaseModel):
    role: Literal["admin", "user"]


class AssignmentRequest(BaseModel):
    assigned: bool


class BulkTrackAssignmentRequest(BaseModel):
    track_ids: list[uuid.UUID] = Field(min_length=1)
    assigned: bool


class BulkModuleAssignmentRequest(BaseModel):
    module_ids: list[uuid.UUID] = Field(min_length=1)
    assigned: bool


class BulkLessonAssignmentRequest(BaseModel):
    lesson_ids: list[uuid.UUID] = Field(min_length=1)
    assigned: bool


class AdminLearningModuleOut(BaseModel):
    id: uuid.UUID
    track_id: uuid.UUID
    title: str
    sort_order: int


class AdminLearningLessonOut(BaseModel):
    id: uuid.UUID
    module_id: uuid.UUID
    title: str
    sort_order: int


class AdminLearningUserOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    project_name: str | None
    company_name: str | None
    assigned_track_ids: list[uuid.UUID]
    assigned_module_ids: list[uuid.UUID]
    assigned_lesson_ids: list[uuid.UUID]


class AdminLearningResponse(BaseModel):
    modules: list[AdminLearningModuleOut]
    lessons: list[AdminLearningLessonOut]
    users: list[AdminLearningUserOut]


class SurveyLevelsResponse(BaseModel):
    levels: dict[uuid.UUID, str]


class AdminSurveyOut(BaseModel):
    """The legacy admin survey-results select list, verbatim."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    score_level: str | None
    usage_band: str | None
    c1_code: str | None
    c2_code: str | None
    c3_code: str | None
    c4_code: str | None
    c5_codes: list[str] | None
    c6_code: str | None
    c1_rung: int | None
    c2_rung: int | None
    c3_rung: int | None
    c4_rung: int | None
    c5_rung: int | None
    c6_rung: int | None
    have_count: int | None
    adv_count: int | None
    safety_flag: bool | None
    mandatory_modules: list[str] | None
    job_title: str | None
    department: str | None
    b_freq: str | None
    b_breadth: str | None
    b_attitude: int | None
    b_readiness: int | None
    b_barriers: list[str] | None
    b_tools: list[str] | None
    b_setup: list[str] | None
    q_excitement: str | None
    q_timesink: str | None
    completed_at: datetime | None
    scored_at: datetime | None


class UserSurveyResponse(BaseModel):
    survey: AdminSurveyOut | None
