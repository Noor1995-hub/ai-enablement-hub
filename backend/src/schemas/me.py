from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

__all__ = ["ComponentState", "JourneyResponse", "UserProfileResponse"]


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: str
    company_id: uuid.UUID | None
    project_id: uuid.UUID | None
    password_set: bool
    external_login: bool
    # Admin rights (spec 2026-10-01-project-scoped-admin-design.md); filled in
    # by the router, so the defaults only apply to model_validate(user).
    is_power_admin: bool = False
    admin_project_ids: list[uuid.UUID] = []
    bypasses_locks: bool = False


class ComponentState(BaseModel):
    hidden: bool
    locked: bool


class JourneyResponse(BaseModel):
    components: dict[str, ComponentState]
    survey_status: Literal["not_started", "in_progress", "complete"]
    learning_status: Literal["not_started", "in_progress", "complete"]
    interview_status: Literal["not_started", "in_progress", "complete"]
