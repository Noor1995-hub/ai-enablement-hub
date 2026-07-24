from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from src.core.constants import COMPONENTS, DEFAULT_HIDDEN, DEFAULT_LOCKED
from src.services.exceptions import DuplicateCompanyNameError, NotFoundError

if TYPE_CHECKING:
    from src.db.models import Company, Project
    from src.repositories.base import AbstractOrgRepository

__all__ = ["OrgService"]

_AI_KINDS = ("chatbot", "assessment", "lesson", "interview")


class OrgService:
    def __init__(self, org: AbstractOrgRepository) -> None:
        self._org = org

    async def companies_with_projects(self) -> list[tuple[Company, list[Project]]]:
        companies = await self._org.list_companies()
        projects = await self._org.list_projects()
        return [
            (company, [p for p in projects if p.company_id == company.id]) for company in companies
        ]

    async def create_company(self, name: str) -> Company:
        name = name.strip()
        if await self._org.get_company_by_name_ci(name) is not None:
            raise DuplicateCompanyNameError
        return await self._org.create_company(name)

    async def create_project(self, name: str, company_id: uuid.UUID) -> Project:
        """Create the project plus its three default component settings rows
        in the same transaction (replaces the legacy two-step insert)."""
        if await self._org.get_company(company_id) is None:
            raise NotFoundError("Company")
        defaults = [
            {"component": comp, "hidden": DEFAULT_HIDDEN[comp], "locked": DEFAULT_LOCKED[comp]}
            for comp in COMPONENTS
        ]
        return await self._org.create_project_with_default_components(
            name.strip(), company_id, defaults
        )

    async def resolve_components(
        self, project_id: uuid.UUID | None, *, require_project: bool = False
    ) -> dict[str, dict[str, bool]]:
        """hidden/locked per component with DEFAULT_* fallback for missing rows.

        project_id None (user without a project) resolves to pure defaults.
        """
        rows = []
        if project_id is not None:
            if require_project and await self._org.get_project(project_id) is None:
                raise NotFoundError("Project")
            rows = await self._org.get_component_settings(project_id)
        by_component = {row.component: row for row in rows}
        return {
            comp: {
                "hidden": by_component[comp].hidden
                if comp in by_component
                else DEFAULT_HIDDEN[comp],
                "locked": by_component[comp].locked
                if comp in by_component
                else DEFAULT_LOCKED[comp],
            }
            for comp in COMPONENTS
        }

    async def set_component(
        self,
        project_id: uuid.UUID,
        component: str,
        *,
        hidden: bool | None,
        locked: bool | None,
    ) -> None:
        """Partial upsert: unspecified flags keep the stored value (or default)."""
        if await self._org.get_project(project_id) is None:
            raise NotFoundError("Project")
        current = next(
            (
                row
                for row in await self._org.get_component_settings(project_id)
                if row.component == component
            ),
            None,
        )
        if hidden is None:
            hidden = current.hidden if current is not None else DEFAULT_HIDDEN[component]
        if locked is None:
            locked = current.locked if current is not None else DEFAULT_LOCKED[component]
        await self._org.upsert_component_setting(
            project_id, component, hidden=hidden, locked=locked
        )

    async def resolve_ai_settings(self, project_id: uuid.UUID | None) -> dict[str, bool]:
        """enabled per AI kind, False fallback for missing rows or no project."""
        if project_id is None:
            return dict.fromkeys(_AI_KINDS, False)
        rows = await self._org.get_ai_settings(project_id)
        by_kind = {row.kind: row.enabled for row in rows}
        return {kind: by_kind.get(kind, False) for kind in _AI_KINDS}

    async def set_ai_surface(self, project_id: uuid.UUID, kind: str, *, enabled: bool) -> None:
        if await self._org.get_project(project_id) is None:
            raise NotFoundError("Project")
        await self._org.upsert_ai_setting(project_id, kind, enabled=enabled)
