"""AdminScope / AdminScopeService rules (spec 2026-10-01-project-scoped-admin-design.md)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.services.admin_scope_service import AdminScope, AdminScopeService
from src.services.exceptions import AdminTargetForbiddenError, InvalidRequestError, NotFoundError

A, B = uuid.uuid4(), uuid.uuid4()


def _user(role: str = "user", project_id: uuid.UUID | None = None) -> Any:
    return SimpleNamespace(id=uuid.uuid4(), role=role, project_id=project_id)


def _service(
    admin_projects: frozenset[uuid.UUID] = frozenset(), targets: dict[uuid.UUID, Any] | None = None
) -> tuple[AdminScopeService, AsyncMock]:
    users = AsyncMock()
    admins = AsyncMock()
    admins.project_ids_for.return_value = admin_projects
    admins.is_project_admin.return_value = False
    known = targets or {}
    users.get_by_id.side_effect = known.get
    users.project_ids_of.side_effect = lambda ids: {
        i: known[i].project_id for i in ids if i in known
    }
    return AdminScopeService(users, admins), admins


def _scope(user: Any, *projects: uuid.UUID, power: bool = False) -> AdminScope:
    return AdminScope(user=user, is_power=power, project_ids=frozenset(projects))


def test_covers() -> None:
    power = _scope(_user("admin"), power=True)
    pa = _scope(_user(), A)
    assert power.covers(B) and power.covers(None)
    assert pa.covers(A)
    assert not pa.covers(B)
    assert not pa.covers(None)


def test_resolve_list_project() -> None:
    assert _scope(_user("admin"), power=True).resolve_list_project(None) is None
    assert _scope(_user("admin"), power=True).resolve_list_project(B) == B
    pa = _scope(_user(), A)
    assert pa.resolve_list_project(None) == A
    assert pa.resolve_list_project(A) == A
    with pytest.raises(NotFoundError):
        pa.resolve_list_project(B)
    with pytest.raises(InvalidRequestError):
        _scope(_user(), A, B).resolve_list_project(None)


async def test_scope_for() -> None:
    service, _ = _service()
    power = await service.scope_for(_user("admin"))
    assert power is not None and power.is_power
    assert await service.scope_for(_user()) is None
    service, _ = _service(frozenset({A}))
    scope = await service.scope_for(_user())
    assert scope is not None
    assert not scope.is_power
    assert scope.project_ids == frozenset({A})


async def test_ensure_user_in_scope_rules() -> None:
    caller = _user(project_id=A)
    learner_a, learner_b, power = _user(project_id=A), _user(project_id=B), _user("admin", A)
    targets = {u.id: u for u in (caller, learner_a, learner_b, power)}
    service, admins = _service(targets=targets)
    scope = _scope(caller, A)

    assert await service.ensure_user_in_scope(scope, learner_a.id) is learner_a
    with pytest.raises(NotFoundError):
        await service.ensure_user_in_scope(scope, learner_b.id)
    with pytest.raises(NotFoundError):
        await service.ensure_user_in_scope(scope, uuid.uuid4())
    with pytest.raises(AdminTargetForbiddenError):
        await service.ensure_user_in_scope(scope, power.id)
    with pytest.raises(AdminTargetForbiddenError):
        await service.ensure_user_in_scope(scope, caller.id)
    admins.is_project_admin.return_value = True
    with pytest.raises(AdminTargetForbiddenError):
        await service.ensure_user_in_scope(scope, learner_a.id)


async def test_power_admin_reaches_any_existing_user() -> None:
    learner_b = _user(project_id=B)
    service, _ = _service(targets={learner_b.id: learner_b})
    power = _scope(_user("admin"), power=True)
    assert await service.ensure_user_in_scope(power, learner_b.id) is learner_b
    with pytest.raises(NotFoundError):
        await service.ensure_user_in_scope(power, uuid.uuid4())


async def test_ensure_users_in_scope_is_all_or_nothing() -> None:
    a1, a2, b1 = _user(project_id=A), _user(project_id=A), _user(project_id=B)
    service, _ = _service(targets={u.id: u for u in (a1, a2, b1)})
    scope = _scope(_user(), A)
    await service.ensure_users_in_scope(scope, [a1.id, a2.id])
    await service.ensure_users_in_scope(scope, [a1.id, a1.id])  # duplicates are fine
    with pytest.raises(NotFoundError):
        await service.ensure_users_in_scope(scope, [a1.id, b1.id])
    with pytest.raises(NotFoundError):
        await service.ensure_users_in_scope(scope, [a1.id, uuid.uuid4()])


async def test_bypasses_locks() -> None:
    service, _ = _service()
    assert await service.bypasses_locks(_user("admin"))
    assert not await service.bypasses_locks(_user(project_id=A))
    service, _ = _service(frozenset({A}))
    assert await service.bypasses_locks(_user(project_id=A))
    assert not await service.bypasses_locks(_user(project_id=B))
    assert not await service.bypasses_locks(_user(project_id=None))
