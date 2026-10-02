from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.core.dependencies.admin_scope import AdminScopeDep, get_admin_scope
from src.core.dependencies.domain import get_dashboard_service
from src.schemas.admin_dashboard import DashboardResponse
from src.services.dashboard_service import DashboardService

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin", tags=["admin:dashboard"], dependencies=[Depends(get_admin_scope)]
)

DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_service: DashboardServiceDep,
    scope: AdminScopeDep,
    project_id: Annotated[uuid.UUID | None, Query()] = None,
) -> DashboardResponse:
    """One call for the whole dashboard screen (spec §4.4). `project_id` scopes
    every aggregate to a single project; omitting it reports across all
    projects (power admins only; a project admin is limited to their project).
    Unknown or out-of-scope `project_id` -> 404."""
    overview = await dashboard_service.overview(scope.resolve_list_project(project_id))
    return DashboardResponse.model_validate(overview)
