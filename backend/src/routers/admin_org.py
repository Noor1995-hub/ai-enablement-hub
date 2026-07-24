from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status

from src.core.dependencies.auth import require_admin
from src.core.dependencies.domain import get_org_service
from src.db.models import Company, Project
from src.schemas.admin_org import (
    AiSettingsResponse,
    AiSurfaceState,
    AiSurfaceUpdateRequest,
    CompaniesResponse,
    CompanyCreateRequest,
    CompanyOut,
    CompanyWithProjects,
    ComponentsResponse,
    ComponentUpdateRequest,
    ProjectCreateRequest,
    ProjectOut,
)
from src.schemas.me import ComponentState
from src.services.org_service import OrgService

__all__ = ["router"]

router = APIRouter(prefix="/api/admin", tags=["admin:org"], dependencies=[Depends(require_admin)])

OrgServiceDep = Annotated[OrgService, Depends(get_org_service)]


@router.get("/companies", response_model=CompaniesResponse)
async def list_companies(org_service: OrgServiceDep) -> CompaniesResponse:
    pairs = await org_service.companies_with_projects()
    return CompaniesResponse(
        companies=[
            CompanyWithProjects(
                id=company.id,
                name=company.name,
                projects=[ProjectOut.model_validate(project) for project in projects],
            )
            for company, projects in pairs
        ]
    )


@router.post("/companies", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
async def create_company(body: CompanyCreateRequest, org_service: OrgServiceDep) -> Company:
    """409 when a company with the same name (case-insensitive) exists."""
    return await org_service.create_company(body.name)


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreateRequest, org_service: OrgServiceDep) -> Project:
    """Creates the project plus its three default component-settings rows in
    one transaction."""
    return await org_service.create_project(body.name, body.company_id)


@router.get("/projects/{project_id}/components", response_model=ComponentsResponse)
async def get_components(project_id: uuid.UUID, org_service: OrgServiceDep) -> ComponentsResponse:
    components = await org_service.resolve_components(project_id, require_project=True)
    return ComponentsResponse(
        components={comp: ComponentState(**state) for comp, state in components.items()}
    )


@router.put("/projects/{project_id}/components/{component}", status_code=status.HTTP_204_NO_CONTENT)
async def put_component(
    project_id: uuid.UUID,
    component: Literal["assessment", "learning", "interview"],
    body: ComponentUpdateRequest,
    org_service: OrgServiceDep,
) -> None:
    """Partial upsert: omitted flags keep their stored (or default) value."""
    await org_service.set_component(project_id, component, hidden=body.hidden, locked=body.locked)


@router.get("/projects/{project_id}/ai", response_model=AiSettingsResponse)
async def get_ai_settings(project_id: uuid.UUID, org_service: OrgServiceDep) -> AiSettingsResponse:
    settings = await org_service.resolve_ai_settings(project_id)
    return AiSettingsResponse(
        settings={kind: AiSurfaceState(enabled=enabled) for kind, enabled in settings.items()}
    )


@router.put("/projects/{project_id}/ai/{kind}", status_code=status.HTTP_204_NO_CONTENT)
async def put_ai_setting(
    project_id: uuid.UUID,
    kind: Literal["chatbot", "assessment", "lesson", "interview"],
    body: AiSurfaceUpdateRequest,
    org_service: OrgServiceDep,
) -> None:
    await org_service.set_ai_surface(project_id, kind, enabled=body.enabled)
