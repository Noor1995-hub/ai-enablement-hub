"""Delete a project or a company with its users (B6, spec 2026-10-06 decisions
2-3). Members are deleted — their progress, survey, interview, sessions and
grants cascade (every FK into users.id is CASCADE or SET NULL) — except power
admins, who are kept and detached. One commit; repositories only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.services.exceptions import NotFoundError

if TYPE_CHECKING:
    import uuid

    from src.db.models import Project, User
    from src.repositories.base import (
        AbstractOrgRepository,
        AbstractProgressRepository,
        AbstractProjectAdminRepository,
        AbstractUnitOfWork,
        AbstractUserRepository,
    )

__all__ = ["OrgDeletionService", "OrgImpact"]


@dataclass(frozen=True)
class OrgImpact:
    projects: int
    users_deleted: int
    power_admins_kept: int
    project_admin_grants: int
    users_with_progress: int
    # Members deleted with it who administer a project NOT being deleted: the
    # warning names them, so a client project's admin isn't lost silently.
    other_project_admins_deleted: int = 0


class OrgDeletionService:
    def __init__(
        self,
        org: AbstractOrgRepository,
        users: AbstractUserRepository,
        project_admins: AbstractProjectAdminRepository,
        progress: AbstractProgressRepository,
        uow: AbstractUnitOfWork,
    ) -> None:
        self._org = org
        self._users = users
        self._project_admins = project_admins
        self._progress = progress
        self._uow = uow

    async def project_impact(self, project_id: uuid.UUID) -> OrgImpact:
        await self._project(project_id)
        members = await self._users.members_of([project_id], None)
        return await self._impact(members, [project_id], projects=0)

    async def company_impact(self, company_id: uuid.UUID) -> OrgImpact:
        project_ids = await self._company_project_ids(company_id)
        members = await self._users.members_of(project_ids, company_id)
        return await self._impact(members, project_ids, projects=len(project_ids))

    async def delete_project(self, project_id: uuid.UUID) -> OrgImpact:
        project = await self._project(project_id)
        members = await self._users.members_of([project_id], None)
        impact = await self._impact(members, [project_id], projects=0)
        kept = [u for u in members if u.role == "admin"]
        for user in kept:
            await self._users.stage_set_org([user.id], None, user.company_id)
        await self._users.stage_delete_many([u.id for u in members if u.role != "admin"])
        await self._org.stage_delete_project(project)
        await self._uow.commit()
        return impact

    async def delete_company(self, company_id: uuid.UUID) -> OrgImpact:
        company = await self._org.get_company(company_id)
        if company is None:
            raise NotFoundError("Company")
        project_ids = await self._company_project_ids(company_id)
        members = await self._users.members_of(project_ids, company_id)
        impact = await self._impact(members, project_ids, projects=len(project_ids))
        kept = [u.id for u in members if u.role == "admin"]
        if kept:
            await self._users.stage_set_org(kept, None, None)
        await self._users.stage_delete_many([u.id for u in members if u.role != "admin"])
        await self._org.stage_delete_company(company)
        await self._uow.commit()
        return impact

    async def _project(self, project_id: uuid.UUID) -> Project:
        project = await self._org.get_project(project_id)
        if project is None:
            raise NotFoundError("Project")
        return project

    async def _company_project_ids(self, company_id: uuid.UUID) -> list[uuid.UUID]:
        if await self._org.get_company(company_id) is None:
            raise NotFoundError("Company")
        return [p.id for p in await self._org.list_projects() if p.company_id == company_id]

    async def _impact(
        self, members: list[User], project_ids: list[uuid.UUID], *, projects: int
    ) -> OrgImpact:
        deleted = [u.id for u in members if u.role != "admin"]
        grants = 0
        for project_id in project_ids:
            grants += len(await self._project_admins.admin_ids_for_project(project_id))
        with_progress = await self._progress.latest_completion_by_user(deleted) if deleted else {}
        doomed = set(project_ids)
        grants_by_user = await self._project_admins.project_ids_by_user(deleted) if deleted else {}
        other_admins = sum(
            1 for projects in grants_by_user.values() if any(p not in doomed for p in projects)
        )
        return OrgImpact(
            projects=projects,
            users_deleted=len(deleted),
            power_admins_kept=len(members) - len(deleted),
            project_admin_grants=grants,
            users_with_progress=len(with_progress),
            other_project_admins_deleted=other_admins,
        )
