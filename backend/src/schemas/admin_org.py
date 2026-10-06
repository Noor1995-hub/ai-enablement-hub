from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from src.schemas._validators import require_non_blank
from src.schemas.me import ComponentState

__all__ = [
    "AiSettingsResponse",
    "AiSurfaceState",
    "AiSurfaceUpdateRequest",
    "CompaniesResponse",
    "CompanyCreateRequest",
    "CompanyOut",
    "CompanyWithProjects",
    "ComponentUpdateRequest",
    "ComponentsResponse",
    "OrgImpactResponse",
    "ProjectCreateRequest",
    "ProjectOut",
    "RenameRequest",
]


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    company_id: uuid.UUID
    created_at: datetime


class CompanyWithProjects(BaseModel):
    id: uuid.UUID
    name: str
    projects: list[ProjectOut]


class CompaniesResponse(BaseModel):
    companies: list[CompanyWithProjects]


class CompanyCreateRequest(BaseModel):
    name: str

    _non_blank = field_validator("name")(require_non_blank)


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class ProjectCreateRequest(BaseModel):
    name: str
    company_id: uuid.UUID

    _non_blank = field_validator("name")(require_non_blank)


class ComponentsResponse(BaseModel):
    components: dict[str, ComponentState]


class ComponentUpdateRequest(BaseModel):
    hidden: bool | None = None
    locked: bool | None = None


class AiSurfaceState(BaseModel):
    enabled: bool


class AiSettingsResponse(BaseModel):
    settings: dict[str, AiSurfaceState]


class AiSurfaceUpdateRequest(BaseModel):
    enabled: bool


def _not_null(value: object) -> object:
    if value is None:
        msg = "must not be null"
        raise ValueError(msg)
    return value


class RenameRequest(BaseModel):
    """B6: rename a project or a company."""

    name: str

    _non_blank = field_validator("name")(require_non_blank)
    _not_null = field_validator("name", mode="before")(_not_null)


class OrgImpactResponse(BaseModel):
    """What a project/company delete takes with it (B6): counts only."""

    model_config = ConfigDict(from_attributes=True)

    projects: int
    users_deleted: int
    power_admins_kept: int
    project_admin_grants: int
    users_with_progress: int
    other_project_admins_deleted: int
