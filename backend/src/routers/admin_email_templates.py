from __future__ import annotations

import uuid
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, status

from src.core.configs.settings import Settings
from src.core.dependencies.auth import require_admin
from src.core.dependencies.domain import get_email_template_service
from src.core.dependencies.settings import get_settings
from src.schemas.email_templates import (
    EmailTemplateOut,
    EmailTemplatePreviewRequest,
    EmailTemplatePreviewResponse,
    EmailTemplatesResponse,
    EmailTemplateUpdateRequest,
)
from src.services.email_template_service import EmailTemplateService

__all__ = ["router"]

router = APIRouter(
    prefix="/api/admin", tags=["admin:email-templates"], dependencies=[Depends(require_admin)]
)

EmailTemplateServiceDep = Annotated[EmailTemplateService, Depends(get_email_template_service)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

# Path param for the two customizable email kinds.
Purpose = Literal["invite", "reset"]


@router.get("/projects/{project_id}/email-templates", response_model=EmailTemplatesResponse)
async def get_email_templates(
    project_id: uuid.UUID, service: EmailTemplateServiceDep
) -> EmailTemplatesResponse:
    """Both invite + reset templates, resolved to the per-project override or the
    code default (`is_custom` distinguishes the two)."""
    resolved = await service.get_templates(project_id)
    return EmailTemplatesResponse(
        templates=[
            EmailTemplateOut(
                # get_templates resolves exactly the two Purpose values.
                purpose=cast("Purpose", item.purpose),
                subject=item.subject,
                body_markdown=item.body_markdown,
                is_custom=item.is_custom,
            )
            for item in resolved
        ]
    )


@router.put(
    "/projects/{project_id}/email-templates/{purpose}", status_code=status.HTTP_204_NO_CONTENT
)
async def put_email_template(
    project_id: uuid.UUID,
    purpose: Purpose,
    body: EmailTemplateUpdateRequest,
    service: EmailTemplateServiceDep,
) -> None:
    """Store (or replace) the per-project override. 400 if the body is blank,
    references an unknown token, or omits the required link token."""
    await service.set_template(project_id, purpose, body.subject, body.body_markdown)


@router.delete(
    "/projects/{project_id}/email-templates/{purpose}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_email_template(
    project_id: uuid.UUID, purpose: Purpose, service: EmailTemplateServiceDep
) -> None:
    """Drop the override so the project falls back to the code default."""
    await service.clear_template(project_id, purpose)


@router.post(
    "/projects/{project_id}/email-templates/{purpose}/preview",
    response_model=EmailTemplatePreviewResponse,
)
async def preview_email_template(
    project_id: uuid.UUID,
    purpose: Purpose,
    body: EmailTemplatePreviewRequest,
    service: EmailTemplateServiceDep,
    settings: SettingsDep,
) -> EmailTemplatePreviewResponse:
    """Render an unsaved draft server-side (same pipeline as a real send) with
    sample token values — the admin's faithful preview."""
    content = await service.preview(
        project_id,
        purpose,
        subject=body.subject,
        body_markdown=body.body_markdown,
        app_url=settings.app.url,
        ttl_days=settings.auth.invite_ttl_days
        if purpose == "invite"
        else settings.auth.reset_ttl_days,
    )
    return EmailTemplatePreviewResponse(
        subject=content.subject, html=content.html, plain_text=content.plain_text
    )
