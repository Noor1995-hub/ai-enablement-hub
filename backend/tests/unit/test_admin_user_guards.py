"""AdminUserService self / last-power-admin guards. The last-power-admin path
is unreachable through the API today (only power admins can demote or delete a
power admin, and the self guard fires first), so it is pinned here as defence
in depth with mocked repositories."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.services.admin_user_service import AdminUserService
from src.services.exceptions import LastPowerAdminError, SelfModificationError


def _user(role: str = "user") -> Any:
    return SimpleNamespace(id=uuid.uuid4(), role=role)


def _service(target: Any, power_admins: int) -> tuple[AdminUserService, AsyncMock]:
    users = AsyncMock()
    users.get_by_id.return_value = target
    users.count_power_admins.return_value = power_admins
    repos = [AsyncMock() for _ in range(6)]
    return AdminUserService(users, *repos, project_admins=AsyncMock(), uow=AsyncMock()), users


async def test_last_power_admin_cannot_be_demoted() -> None:
    target = _user("admin")
    service, users = _service(target, power_admins=1)
    with pytest.raises(LastPowerAdminError):
        await service.set_role(_user("admin"), target.id, "user")
    users.update_role.assert_not_awaited()


async def test_last_power_admin_cannot_be_deleted() -> None:
    target = _user("admin")
    service, users = _service(target, power_admins=1)
    with pytest.raises(LastPowerAdminError):
        await service.delete_user(_user("admin"), target.id)
    users.delete.assert_not_awaited()


async def test_self_guard_fires_first() -> None:
    actor = _user("admin")
    service, users = _service(actor, power_admins=5)
    with pytest.raises(SelfModificationError):
        await service.set_role(actor, actor.id, "user")
    with pytest.raises(SelfModificationError):
        await service.delete_user(actor, actor.id)
    users.update_role.assert_not_awaited()
    users.delete.assert_not_awaited()


async def test_demoting_one_of_several_power_admins_is_allowed() -> None:
    target = _user("admin")
    service, users = _service(target, power_admins=2)
    await service.set_role(_user("admin"), target.id, "user")
    users.update_role.assert_awaited_once_with(target, "user")
