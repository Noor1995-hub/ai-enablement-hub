from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

__all__ = [
    "AdminLearningLessonOut",
    "AdminLearningModuleOut",
    "AdminLearningResponse",
    "AdminLearningUserOut",
    "AdminSurveyOut",
    "AdminUserOut",
    "AdminUsersResponse",
    "AssignmentRequest",
    "BulkAssignmentRequest",
    "BulkInviteReport",
    "BulkInviteRow",
    "BulkInviteSummary",
    "BulkLessonAssignmentRequest",
    "BulkModuleAssignmentRequest",
    "BulkTrackAssignmentRequest",
    "EmailStatus",
    "InviteRequest",
    "LinkResponse",
    "MaturityOverrideRequest",
    "ReminderResponse",
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
    # maturity_override = the admin pin (null = from assessment); effective =
    # the resolved level (override or assessment, raised by completion). The
    # admin table shows effective with a pin indicator when overridden.
    maturity_override: str | None
    effective_maturity: str | None
    # Task 8 status/progress/attention/provenance enrichment (all additive).
    # last_active_at = latest refresh-session use (null = never active);
    # activated = password_set OR external_id linked; the two lesson counts are
    # summed over the user's assigned lessons; needs_attention/attention_reason
    # come from core.attention.attention_for; the default_* lists carry the
    # "assigned via project default" provenance (the matrix's "via default" tint).
    last_active_at: datetime | None
    activated: bool
    assigned_lesson_count: int
    completed_lesson_count: int
    needs_attention: bool
    attention_reason: str | None
    default_track_ids: list[uuid.UUID]
    default_module_ids: list[uuid.UUID]
    default_lesson_ids: list[uuid.UUID]


class AdminUsersResponse(BaseModel):
    users: list[AdminUserOut]
    # Task 9: total AFTER q/status filtering, BEFORE limit/offset slicing —
    # additive; the old admin panel (no query params) ignores unknown fields.
    total: int


class InviteRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    project_id: uuid.UUID
    send_email: bool = True

    _non_blank = field_validator("first_name", "last_name")(_require_non_blank)


# "sent" = ACS accepted the message; "failed" = send errored (admin shares the
# link manually); "disabled" = EMAIL__* unconfigured; "skipped" = the admin
# chose the link-only path (send_email=False) — email was never attempted.
EmailStatus = Literal["sent", "failed", "disabled", "skipped"]


class LinkResponse(BaseModel):
    link: str
    email_status: EmailStatus


class ReminderResponse(BaseModel):
    # Never "skipped" — the reminder endpoint has no link-only variant.
    email_status: EmailStatus


class BulkInviteRow(BaseModel):
    row_number: int
    first_name: str
    last_name: str
    email: str
    # preview: valid | duplicate | invalid ; commit turns each "valid" into
    # "created" or "email_failed".
    status: Literal["valid", "duplicate", "invalid", "created", "email_failed"]
    detail: str | None = None


class BulkInviteSummary(BaseModel):
    total_rows: int
    valid: int
    duplicates: int
    invalid: int
    created: int  # 0 on dry_run
    email_failed: int  # 0 on dry_run


class BulkInviteReport(BaseModel):
    dry_run: bool
    project_id: uuid.UUID
    summary: BulkInviteSummary
    rows: list[BulkInviteRow]


class RoleUpdateRequest(BaseModel):
    # "user+" bypasses learning-path locks but holds no admin powers (require_admin
    # still gates on == "admin"); see the 2026-07-22 user-plus-role spec.
    role: Literal["admin", "user+", "user"]


class MaturityOverrideRequest(BaseModel):
    # null clears the pin (fall back to assessment + earned progression). Any of
    # the four ladder levels may be pinned, including the aspirational
    # `multiplier`; the assessment itself only ever yields the first three.
    level: Literal["explore", "practitioner", "integrator", "multiplier"] | None


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


class BulkAssignmentRequest(BaseModel):
    """Many-users × one content kind (spec §4.2). Exactly one of the three id
    lists must be provided; all provided lists must be non-empty."""

    user_ids: list[uuid.UUID] = Field(min_length=1)
    track_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    module_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    lesson_ids: list[uuid.UUID] | None = Field(default=None, min_length=1)
    assigned: bool

    @model_validator(mode="after")
    def _exactly_one_kind(self) -> BulkAssignmentRequest:
        provided = [x for x in (self.track_ids, self.module_ids, self.lesson_ids) if x is not None]
        if len(provided) != 1:
            msg = "provide exactly one of track_ids, module_ids or lesson_ids"
            raise ValueError(msg)
        return self


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
    # Task 8: the "assigned via project default" provenance for the matrix tint.
    default_track_ids: list[uuid.UUID]
    default_module_ids: list[uuid.UUID]
    default_lesson_ids: list[uuid.UUID]


class AdminLearningResponse(BaseModel):
    modules: list[AdminLearningModuleOut]
    lessons: list[AdminLearningLessonOut]
    users: list[AdminLearningUserOut]
    # Task 9: total users AFTER project_id filtering, BEFORE limit/offset
    # slicing — modules/lessons are never paginated. Additive field.
    total: int


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
