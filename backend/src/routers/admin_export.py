"""Project data export (#92): GET /api/admin/projects/{project_id}/export.

Gated by the project scope (spec 2026-10-01-project-scoped-admin-design.md): a
project admin exports only the projects they run, a power admin any project.
The file holds learners' personal data (SECURITY.md); the log line names the
caller, the project and the sections by id only, never an email."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from src.core.dependencies.admin_scope import require_project_in_scope
from src.core.dependencies.export import get_project_export_service
from src.schemas.admin_export import EXPORT_SECTIONS, ExportSection
from src.services.admin_scope_service import AdminScope
from src.services.project_export_service import ProjectExportService

__all__ = ["router"]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin:export"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/projects/{project_id}/export",
    response_class=Response,
    responses={200: {"content": {_XLSX: {"schema": {"type": "string", "format": "binary"}}}}},
)
async def export_project(
    project_id: uuid.UUID,
    scope: Annotated[AdminScope, Depends(require_project_in_scope)],
    service: Annotated[ProjectExportService, Depends(get_project_export_service)],
    sections: Annotated[list[ExportSection], Query(min_length=1)],
) -> Response:
    """One .xlsx of the project's learners, one sheet per requested section
    (repeat the parameter: `?sections=people&sections=assessment`). Unknown
    section -> 422; unknown or out-of-scope project -> 404."""
    chosen = [section for section in EXPORT_SECTIONS if section in sections]
    export = await service.export(project_id, chosen)
    logger.info(
        "project export: project=%s sections=%s by=%s",
        project_id,
        ",".join(chosen),
        scope.user.id,
    )
    return Response(
        content=export.content,
        media_type=_XLSX,
        headers={
            "Content-Disposition": f'attachment; filename="{export.filename}"',
            "Cache-Control": "no-store",
        },
    )
