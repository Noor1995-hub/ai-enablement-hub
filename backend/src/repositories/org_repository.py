from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import (
    Company,
    Project,
    ProjectAiSetting,
    ProjectComponentSetting,
    ProjectTrackDefault,
)
from src.repositories.base import AbstractOrgRepository

__all__ = ["OrgRepository"]


class OrgRepository(AbstractOrgRepository):
    async def list_companies(self) -> list[Company]:
        result = await self._session.execute(select(Company).order_by(Company.name))
        return list(result.scalars().all())

    async def list_projects(self) -> list[Project]:
        result = await self._session.execute(select(Project).order_by(Project.name))
        return list(result.scalars().all())

    async def get_company_by_name_ci(self, name: str) -> Company | None:
        result = await self._session.execute(
            select(Company).where(func.lower(Company.name) == name.lower())
        )
        return result.scalars().first()

    async def create_company(self, name: str) -> Company:
        company = Company(name=name)
        self._session.add(company)
        await self._session.commit()
        await self._session.refresh(company)
        return company

    async def get_company(self, company_id: uuid.UUID) -> Company | None:
        result = await self._session.execute(select(Company).where(Company.id == company_id))
        return result.scalar_one_or_none()

    async def get_project(self, project_id: uuid.UUID) -> Project | None:
        result = await self._session.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def create_project_with_default_components(
        self, name: str, company_id: uuid.UUID, defaults: list[dict[str, Any]]
    ) -> Project:
        project = Project(name=name, company_id=company_id)
        self._session.add(project)
        await self._session.flush()
        self._session.add_all(
            ProjectComponentSetting(project_id=project.id, **row) for row in defaults
        )
        await self._session.commit()
        await self._session.refresh(project)
        return project

    async def get_component_settings(self, project_id: uuid.UUID) -> list[ProjectComponentSetting]:
        result = await self._session.execute(
            select(ProjectComponentSetting).where(ProjectComponentSetting.project_id == project_id)
        )
        return list(result.scalars().all())

    async def upsert_component_setting(
        self, project_id: uuid.UUID, component: str, *, hidden: bool, locked: bool
    ) -> None:
        stmt = pg_insert(ProjectComponentSetting).values(
            project_id=project_id, component=component, hidden=hidden, locked=locked
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["project_id", "component"],
            set_={
                "hidden": stmt.excluded.hidden,
                "locked": stmt.excluded.locked,
                "updated_at": func.now(),
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def get_ai_settings(self, project_id: uuid.UUID) -> list[ProjectAiSetting]:
        # populate_existing: upsert_ai_setting below writes via a raw ON CONFLICT
        # DO UPDATE, which never touches the ORM identity map — without this, a
        # row already loaded earlier in the same session would keep returning
        # its pre-upsert (stale) `enabled` value instead of the fresh one.
        result = await self._session.execute(
            select(ProjectAiSetting)
            .where(ProjectAiSetting.project_id == project_id)
            .execution_options(populate_existing=True)
        )
        return list(result.scalars().all())

    async def upsert_ai_setting(self, project_id: uuid.UUID, kind: str, *, enabled: bool) -> None:
        stmt = pg_insert(ProjectAiSetting).values(project_id=project_id, kind=kind, enabled=enabled)
        stmt = stmt.on_conflict_do_update(
            index_elements=["project_id", "kind"],
            set_={"enabled": stmt.excluded.enabled, "updated_at": func.now()},
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def default_track_ids(self, project_id: uuid.UUID) -> list[uuid.UUID]:
        result = await self._session.execute(
            select(ProjectTrackDefault.track_id).where(ProjectTrackDefault.project_id == project_id)
        )
        return list(result.scalars().all())

    async def set_default_tracks(self, project_id: uuid.UUID, track_ids: list[uuid.UUID]) -> None:
        await self._session.execute(
            delete(ProjectTrackDefault).where(ProjectTrackDefault.project_id == project_id)
        )
        self._session.add_all(
            ProjectTrackDefault(project_id=project_id, track_id=track_id) for track_id in track_ids
        )
        await self._session.commit()

    async def rename_company(self, company: Company, name: str) -> Company:
        company.name = name
        await self._session.commit()
        await self._session.refresh(company)
        return company

    async def rename_project(self, project: Project, name: str) -> Project:
        project.name = name
        await self._session.commit()
        await self._session.refresh(project)
        return project

    async def stage_delete_project(self, project: Project) -> None:
        await self._session.delete(project)
        await self._session.flush()

    async def stage_delete_company(self, company: Company) -> None:
        # projects.company_id is ON DELETE CASCADE; users pointing at the
        # company (RESTRICT) are deleted or detached first (OrgDeletionService).
        await self._session.delete(company)
        await self._session.flush()
