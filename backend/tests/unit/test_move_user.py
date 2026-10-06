from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import (
    AbstractAssignmentRepository,
    AbstractAuthSessionRepository,
    AbstractContentRepository,
    AbstractOrgRepository,
    AbstractProgressRepository,
    AbstractProjectAdminRepository,
    AbstractSurveyRepository,
    AbstractUnitOfWork,
    AbstractUserRepository,
)
from src.services.admin_user_service import AdminUserService
from src.services.exceptions import NotFoundError

OLD, NEW, COMPANY = (uuid.uuid4() for _ in range(3))


def _service(user: SimpleNamespace | None, project: SimpleNamespace | None):  # noqa: ANN202
    users = AsyncMock(spec=AbstractUserRepository)
    users.get_by_id.return_value = user
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_project.return_value = project
    admins = AsyncMock(spec=AbstractProjectAdminRepository)
    admins.project_ids_for.return_value = frozenset()
    uow = AsyncMock(spec=AbstractUnitOfWork)
    service = AdminUserService(
        users,
        org,
        AsyncMock(spec=AbstractAssignmentRepository),
        AsyncMock(spec=AbstractContentRepository),
        AsyncMock(spec=AbstractSurveyRepository),
        AsyncMock(spec=AbstractAuthSessionRepository),
        AsyncMock(spec=AbstractProgressRepository),
        project_admins=admins,
        uow=uow,
    )
    return service, users, admins, uow


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), project_id=OLD, company_id=uuid.uuid4(), role="user")


async def test_move_sets_project_and_its_company_in_one_commit() -> None:
    user = _user()
    service, users, admins, uow = _service(user, SimpleNamespace(id=NEW, company_id=COMPANY))

    await service.move_user(user.id, NEW)

    users.stage_set_org.assert_awaited_once_with([user.id], NEW, COMPANY)
    admins.stage_revoke.assert_not_awaited()
    uow.commit.assert_awaited_once()


async def test_move_into_a_project_you_run_drops_only_that_grant() -> None:
    user = _user()
    service, _, admins, _ = _service(user, SimpleNamespace(id=NEW, company_id=COMPANY))
    admins.project_ids_for.return_value = frozenset({NEW, uuid.uuid4()})

    await service.move_user(user.id, NEW)

    admins.stage_revoke.assert_awaited_once_with(user.id, NEW)


async def test_moving_to_the_current_project_changes_nothing() -> None:
    user = _user()
    service, users, _, uow = _service(user, SimpleNamespace(id=OLD, company_id=COMPANY))
    await service.move_user(user.id, OLD)
    users.stage_set_org.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.parametrize("missing", ["user", "project"])
async def test_unknown_user_or_project_is_404(missing: str) -> None:
    user = _user()
    service, _, _, _ = _service(
        None if missing == "user" else user,
        None if missing == "project" else SimpleNamespace(id=NEW, company_id=COMPANY),
    )
    with pytest.raises(NotFoundError):
        await service.move_user(uuid.uuid4(), NEW)
