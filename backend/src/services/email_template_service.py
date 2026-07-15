from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, NamedTuple

from src.services.email_templates import (
    DEFAULT_TEMPLATES,
    build_tokens,
    render_email,
    validate_template,
)
from src.services.exceptions import NotFoundError

if TYPE_CHECKING:
    from src.db.models import Project
    from src.repositories.base import (
        AbstractEmailTemplateRepository,
        AbstractOrgRepository,
    )
    from src.services.email_templates import EmailContent

__all__ = ["EmailTemplateService", "ResolvedTemplate"]


class ResolvedTemplate(NamedTuple):
    purpose: str
    subject: str
    body_markdown: str
    is_custom: bool


class EmailTemplateService:
    """Resolves the per-project invite/reset template (override → code default),
    renders it for the send path, previews unsaved drafts, and validates + stores
    admin edits. Uses the org repo only to check project existence / read the
    project name token — it never calls another service."""

    _PURPOSES = ("invite", "reset")

    def __init__(
        self,
        templates: AbstractEmailTemplateRepository,
        org: AbstractOrgRepository,
    ) -> None:
        self._templates = templates
        self._org = org

    async def _get_project_or_404(self, project_id: uuid.UUID) -> Project:
        project = await self._org.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        return project

    async def resolve(self, project_id: uuid.UUID | None, purpose: str) -> ResolvedTemplate:
        """The effective template, custom row if one exists else the code default.
        Lenient (no project check) — used by the resilient send path."""
        row = await self._templates.get(project_id, purpose) if project_id is not None else None
        if row is not None:
            return ResolvedTemplate(purpose, row.subject, row.body_markdown, True)
        default = DEFAULT_TEMPLATES[purpose]
        return ResolvedTemplate(purpose, default.subject, default.body_markdown, False)

    async def get_templates(self, project_id: uuid.UUID) -> list[ResolvedTemplate]:
        """Both purposes resolved for the admin editor (404 for unknown project)."""
        await self._get_project_or_404(project_id)
        by_purpose = {
            row.purpose: row for row in await self._templates.list_for_project(project_id)
        }
        resolved: list[ResolvedTemplate] = []
        for purpose in self._PURPOSES:
            row = by_purpose.get(purpose)
            if row is not None:
                resolved.append(ResolvedTemplate(purpose, row.subject, row.body_markdown, True))
            else:
                default = DEFAULT_TEMPLATES[purpose]
                resolved.append(
                    ResolvedTemplate(purpose, default.subject, default.body_markdown, False)
                )
        return resolved

    async def set_template(
        self, project_id: uuid.UUID, purpose: str, subject: str, body_markdown: str
    ) -> None:
        await self._get_project_or_404(project_id)
        validate_template(purpose, subject, body_markdown)
        await self._templates.upsert(
            project_id, purpose, subject=subject, body_markdown=body_markdown
        )

    async def clear_template(self, project_id: uuid.UUID, purpose: str) -> None:
        await self._get_project_or_404(project_id)
        await self._templates.delete(project_id, purpose)

    async def render(
        self,
        project_id: uuid.UUID | None,
        purpose: str,
        *,
        first_name: str,
        last_name: str,
        link: str,
        ttl_days: int,
        login_url: str | None = None,
    ) -> EmailContent:
        """Render the resolved template for an actual send."""
        resolved = await self.resolve(project_id, purpose)
        project_name = ""
        if project_id is not None:
            project = await self._org.get_project(project_id)
            project_name = project.name if project is not None else ""
        tokens = build_tokens(
            purpose,
            first_name=first_name,
            last_name=last_name,
            project_name=project_name,
            link=link,
            ttl_days=ttl_days,
            login_url=login_url,
        )
        return render_email(resolved.subject, resolved.body_markdown, tokens=tokens)

    async def preview(
        self,
        project_id: uuid.UUID,
        purpose: str,
        *,
        subject: str,
        body_markdown: str,
        app_url: str,
        ttl_days: int,
    ) -> EmailContent:
        """Render an UNSAVED draft with sample token values (404 for unknown
        project). Uses the real project name so the preview reads true to life."""
        project = await self._get_project_or_404(project_id)
        base = app_url.rstrip("/")
        tokens = build_tokens(
            purpose,
            first_name="Alex",
            last_name="Taylor",
            project_name=project.name,
            link=f"{base}/invite/example-invite-token",
            ttl_days=ttl_days,
            login_url=f"{base}/login",
        )
        return render_email(subject, body_markdown, tokens=tokens)
