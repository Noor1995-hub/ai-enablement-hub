from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.repositories.base import (
    AbstractOrgRepository,
    AbstractProgressRepository,
    AbstractProjectAdminRepository,
    AbstractUnitOfWork,
    AbstractUserRepository,
)
from src.services.org_deletion_service import OrgDeletionService, OrgImpact

CO = uuid.uuid4()
P1, P2 = uuid.uuid4(), uuid.uuid4()


def _u(role: str = "user", project_id: uuid.UUID | None = P1) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=role, project_id=project_id, company_id=CO)


def _service(members: list[SimpleNamespace]):  # noqa: ANN202
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_project.return_value = SimpleNamespace(id=P1, company_id=CO)
    org.get_company.return_value = SimpleNamespace(id=CO)
    org.list_projects.return_value = [
        SimpleNamespace(id=P1, company_id=CO),
        SimpleNamespace(id=P2, company_id=CO),
        SimpleNamespace(id=uuid.uuid4(), company_id=uuid.uuid4()),
    ]
    users = AsyncMock(spec=AbstractUserRepository)
    users.members_of.return_value = members
    admins = AsyncMock(spec=AbstractProjectAdminRepository)
    admins.admin_ids_for_project.return_value = {uuid.uuid4(), uuid.uuid4()}
    admins.project_ids_by_user.return_value = {}
    progress = AsyncMock(spec=AbstractProgressRepository)
    progress.latest_completion_by_user.side_effect = lambda ids: dict.fromkeys(ids[:1], object())
    uow = AsyncMock(spec=AbstractUnitOfWork)
    return OrgDeletionService(org, users, admins, progress, uow), org, users, uow


async def test_project_impact_counts_members_power_admins_grants_progress() -> None:
    learner, other, power = _u(), _u(), _u("admin")
    service, _, users, _ = _service([learner, other, power])

    impact = await service.project_impact(P1)

    users.members_of.assert_awaited_once_with([P1], None)
    assert impact == OrgImpact(
        projects=0,
        users_deleted=2,
        power_admins_kept=1,
        project_admin_grants=2,
        users_with_progress=1,
    )


async def test_delete_project_keeps_power_admins_project_less() -> None:
    learner, power = _u(), _u("admin")
    service, org, users, uow = _service([learner, power])

    await service.delete_project(P1)

    users.stage_set_org.assert_awaited_once_with([power.id], None, power.company_id)
    users.stage_delete_many.assert_awaited_once_with([learner.id])
    org.stage_delete_project.assert_awaited_once()
    uow.commit.assert_awaited_once()


async def test_delete_project_deletes_members_even_if_they_run_another_project() -> None:
    coach = _u()  # a member of P1 who administers some other project
    service, _, users, _ = _service([coach])
    await service.delete_project(P1)
    users.stage_delete_many.assert_awaited_once_with([coach.id])


async def test_delete_company_covers_its_projects_and_detaches_power_admins_fully() -> None:
    learner, power = _u(project_id=P2), _u("admin")
    service, org, users, _ = _service([learner, power])

    impact = await service.delete_company(CO)

    users.members_of.assert_awaited_once_with([P1, P2], CO)
    users.stage_set_org.assert_awaited_once_with([power.id], None, None)
    users.stage_delete_many.assert_awaited_once_with([learner.id])
    org.stage_delete_company.assert_awaited_once()
    assert impact.projects == 2


async def test_impact_counts_members_who_run_another_project() -> None:
    """A member of the deleted project who administers ANOTHER project loses
    that account too; the warning must say so (B6 review)."""
    coach, learner = _u(), _u()
    service, _, _, _ = _service([coach, learner])
    service._project_admins.project_ids_by_user.return_value = {coach.id: {uuid.uuid4()}}  # noqa: SLF001

    impact = await service.project_impact(P1)

    assert impact.other_project_admins_deleted == 1
