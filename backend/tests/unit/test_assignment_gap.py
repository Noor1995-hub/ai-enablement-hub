"""The assignment gap: lessons of a module that learners who HOLD the module
don't have yet (new or moved lessons). Spec 2026-10-05, decision 4."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import (
    AbstractAssignmentRepository,
    AbstractContentRepository,
    AbstractProjectAdminRepository,
    AbstractUserRepository,
)
from src.services.content_service import AssignmentGap, ContentService
from src.services.exceptions import NotFoundError

MODULE = uuid.uuid4()
PROJECT = uuid.uuid4()
OLD, NEW, ELSEWHERE = (uuid.uuid4() for _ in range(3))


def _user(role: str = "user") -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=role, project_id=PROJECT)


class _World:
    def __init__(self) -> None:
        self.ann, self.bob, self.coach, self.power = _user(), _user(), _user(), _user("admin")
        self.outsider = _user()  # holds the module, other project
        self.content = AsyncMock(spec=AbstractContentRepository)
        self.content.get_module.return_value = SimpleNamespace(id=MODULE)
        self.content.list_lesson_summaries.return_value = [
            SimpleNamespace(id=OLD, module_id=MODULE),
            SimpleNamespace(id=NEW, module_id=MODULE),
            SimpleNamespace(id=ELSEWHERE, module_id=uuid.uuid4()),
        ]
        self.assignments = AsyncMock(spec=AbstractAssignmentRepository)
        holders = [self.ann, self.bob, self.coach, self.power, self.outsider]
        self.assignments.user_ids_with_module.return_value = {u.id for u in holders}
        self.assignments.user_lessons_for_users.return_value = [
            SimpleNamespace(user_id=u.id, lesson_id=OLD) for u in holders
        ] + [SimpleNamespace(user_id=self.bob.id, lesson_id=NEW)]
        self.assignments.add_user_lesson_pairs.side_effect = lambda pairs, **_: len(pairs)
        self.users = AsyncMock(spec=AbstractUserRepository)
        self.users.list_with_org_names.return_value = [
            (u, "Acme", "Rollout") for u in (self.ann, self.bob, self.coach, self.power)
        ]
        self.project_admins = AsyncMock(spec=AbstractProjectAdminRepository)
        self.project_admins.admin_ids_for_project.return_value = {self.coach.id}

    def service(self) -> ContentService:
        return ContentService(
            self.content,
            assignments=self.assignments,
            users=self.users,
            project_admins=self.project_admins,
        )


async def test_gap_for_everyone_who_holds_the_module() -> None:
    world = _World()

    gap = await world.service().assignment_gap(MODULE, None)

    # ann, coach, power, outsider miss NEW; bob has it.
    assert gap == AssignmentGap(lesson_ids=[NEW], learner_count=4, missing_pairs=4)


async def test_project_gap_excludes_other_projects_and_staff() -> None:
    world = _World()

    gap = await world.service().assignment_gap(MODULE, PROJECT)

    assert gap == AssignmentGap(lesson_ids=[NEW], learner_count=1, missing_pairs=1)  # ann only
    world.users.list_with_org_names.assert_awaited_once_with(PROJECT)


async def test_assign_inserts_exactly_the_missing_pairs_as_manual() -> None:
    world = _World()

    inserted = await world.service().assign_gap(MODULE, PROJECT)

    assert inserted == 1
    world.assignments.add_user_lesson_pairs.assert_awaited_once_with(
        [(world.ann.id, NEW)], assigned_via="manual"
    )


async def test_an_empty_gap_inserts_nothing() -> None:
    world = _World()
    world.assignments.user_ids_with_module.return_value = {world.bob.id}

    gap = await world.service().assignment_gap(MODULE, None)

    assert gap == AssignmentGap(lesson_ids=[], learner_count=0, missing_pairs=0)
    assert await world.service().assign_gap(MODULE, None) == 0


async def test_unknown_module_is_404() -> None:
    world = _World()
    world.content.get_module.return_value = None
    with pytest.raises(NotFoundError):
        await world.service().assignment_gap(MODULE, None)
