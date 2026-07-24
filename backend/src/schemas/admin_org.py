from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

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
    "ProjectCreateRequest",
    "ProjectOut",
]


def _require_non_blank(value: str) -> str:
    if not value.strip():
        msg = "must not be blank"
        raise ValueError(msg)
    return value


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

    _non_blank = field_validator("name")(_require_non_blank)


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class ProjectCreateRequest(BaseModel):
    name: str
    company_id: uuid.UUID

    _non_blank = field_validator("name")(_require_non_blank)


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
