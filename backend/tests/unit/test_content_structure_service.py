"""ContentService B4 rules on fake repositories (spec 2026-10-05)."""

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
from src.services.content_service import ContentService, DeleteImpact
from src.services.exceptions import InvalidRequestError, NotFoundError


def _ids(n: int) -> list[uuid.UUID]:
    return [uuid.uuid4() for _ in range(n)]


def _service() -> tuple[ContentService, AsyncMock]:
    content = AsyncMock(spec=AbstractContentRepository)
    service = ContentService(
        content,
        assignments=AsyncMock(spec=AbstractAssignmentRepository),
        users=AsyncMock(spec=AbstractUserRepository),
        project_admins=AsyncMock(spec=AbstractProjectAdminRepository),
    )
    return service, content


async def test_update_track_keeps_type_and_level_independent() -> None:
    service, content = _service()
    track = SimpleNamespace(id=uuid.uuid4(), track_type="general", required_level="explore")
    content.get_track.return_value = track

    await service.update_track(track.id, {"track_type": "tool"})

    content.update_track.assert_awaited_once_with(track, {"track_type": "tool"})


async def test_update_unknown_track_is_404() -> None:
    service, content = _service()
    content.get_track.return_value = None
    with pytest.raises(NotFoundError):
        await service.update_track(uuid.uuid4(), {"name": "x"})


async def test_reorder_tracks_needs_the_exact_set() -> None:
    service, content = _service()
    a, b = _ids(2)
    content.list_tracks.return_value = [SimpleNamespace(id=a), SimpleNamespace(id=b)]

    with pytest.raises(InvalidRequestError):
        await service.reorder_tracks([a])
    await service.reorder_tracks([b, a])

    content.set_track_orders.assert_awaited_once_with([(b, 0), (a, 1)])


async def test_update_module_moves_when_the_track_changes() -> None:
    service, content = _service()
    old_track, new_track = _ids(2)
    module = SimpleNamespace(id=uuid.uuid4(), track_id=old_track)
    content.get_module.return_value = module
    content.get_track.return_value = SimpleNamespace(id=new_track)
    content.move_module.return_value = module

    await service.update_module(module.id, {"title": "New", "track_id": new_track})

    content.move_module.assert_awaited_once_with(module, new_track)
    content.update_module.assert_awaited_once_with(module, {"title": "New"})


async def test_move_module_to_its_own_track_is_a_noop() -> None:
    service, content = _service()
    track_id = uuid.uuid4()
    module = SimpleNamespace(id=uuid.uuid4(), track_id=track_id)
    content.get_module.return_value = module

    await service.update_module(module.id, {"track_id": track_id})

    content.move_module.assert_not_awaited()
    content.update_module.assert_not_awaited()


async def test_reorder_modules_needs_the_tracks_exact_set() -> None:
    service, content = _service()
    track_id = uuid.uuid4()
    a, b = _ids(2)
    content.get_track.return_value = SimpleNamespace(id=track_id)
    content.list_modules.return_value = [SimpleNamespace(id=a), SimpleNamespace(id=b)]

    with pytest.raises(InvalidRequestError):
        await service.reorder_modules(track_id, [a, a])
    await service.reorder_modules(track_id, [b, a])

    content.list_modules.assert_awaited_with(track_id)
    content.set_module_orders.assert_awaited_once_with([(b, 0), (a, 1)])


async def test_prerequisites_refuse_a_cycle_naming_the_module() -> None:
    service, content = _service()
    a, b = _ids(2)
    content.get_module.return_value = SimpleNamespace(id=a, title="Prompting basics")
    content.count_modules_by_ids.return_value = 1
    content.list_prerequisites.return_value = [
        SimpleNamespace(module_id=b, prerequisite_module_id=a)
    ]

    with pytest.raises(InvalidRequestError, match="Prompting basics"):
        await service.set_prerequisites(a, [b])
    content.set_prerequisites.assert_not_awaited()


async def test_prerequisites_dedupe_and_allow_cross_track_chains() -> None:
    service, content = _service()
    a, b = _ids(2)
    content.get_module.return_value = SimpleNamespace(id=a, title="A")
    content.count_modules_by_ids.return_value = 1
    content.list_prerequisites.return_value = []

    await service.set_prerequisites(a, [b, b])

    content.set_prerequisites.assert_awaited_once_with(a, [b])


async def test_prerequisites_with_an_unknown_id_are_404() -> None:
    service, content = _service()
    a, b = _ids(2)
    content.get_module.return_value = SimpleNamespace(id=a, title="A")
    content.count_modules_by_ids.return_value = 0
    with pytest.raises(NotFoundError):
        await service.set_prerequisites(a, [b])


async def test_update_lesson_with_module_id_moves_it() -> None:
    service, content = _service()
    old, new = _ids(2)
    lesson = SimpleNamespace(id=uuid.uuid4(), module_id=old)
    content.get_lesson.return_value = lesson
    content.get_module.return_value = SimpleNamespace(id=new)
    content.move_lesson.return_value = lesson

    await service.update_lesson(lesson.id, {"module_id": new})

    content.move_lesson.assert_awaited_once_with(lesson, new)
    # B5: a move is a content write, so only the stamp follows it.
    _, stamp = content.update_lesson.await_args.args
    assert set(stamp) == {"updated_at", "updated_by"}


async def test_track_impact_counts_everything_below_it() -> None:
    service, content = _service()
    track_id, m1, m2 = _ids(3)
    content.get_track.return_value = SimpleNamespace(id=track_id)
    content.list_modules.return_value = [SimpleNamespace(id=m1), SimpleNamespace(id=m2)]
    lessons = [SimpleNamespace(id=uuid.uuid4(), module_id=m) for m in (m1, m1, m2)]
    content.list_lesson_summaries.return_value = [
        *lessons,
        SimpleNamespace(id=uuid.uuid4(), module_id=uuid.uuid4()),
    ]
    content.learner_counts_for_lessons.return_value = (14, 9)

    impact = await service.track_impact(track_id)

    assert impact == DeleteImpact(
        modules=2, lessons=3, learners_assigned=14, learners_with_progress=9
    )
    content.learner_counts_for_lessons.assert_awaited_once_with([le.id for le in lessons])


async def test_impact_of_an_empty_track_is_zero() -> None:
    service, content = _service()
    content.get_track.return_value = SimpleNamespace(id=uuid.uuid4())
    content.list_modules.return_value = []
    content.list_lesson_summaries.return_value = []
    content.learner_counts_for_lessons.return_value = (0, 0)

    assert await service.track_impact(uuid.uuid4()) == DeleteImpact(0, 0, 0, 0)


async def test_content_tree_nests_counts_and_prerequisites() -> None:
    service, content = _service()
    t, m1, m2 = _ids(3)
    content.list_tracks.return_value = [
        SimpleNamespace(
            id=t,
            name="General I",
            color=None,
            track_type="general",
            required_level="explore",
            is_introduction=False,
            sort_order=0,
        )
    ]
    content.list_modules.return_value = [
        SimpleNamespace(id=m1, track_id=t, title="M1", description=None, sort_order=0),
        SimpleNamespace(id=m2, track_id=t, title="M2", description="d", sort_order=1),
    ]
    content.list_prerequisites.return_value = [
        SimpleNamespace(module_id=m2, prerequisite_module_id=m1)
    ]
    content.list_lesson_summaries.return_value = [
        SimpleNamespace(id=uuid.uuid4(), module_id=m2, title="L", sort_order=0)
    ]

    tree = await service.content_tree()

    assert [m["title"] for m in tree[0]["modules"]] == ["M1", "M2"]
    assert tree[0]["modules"][1]["prerequisite_ids"] == [m1]
    assert tree[0]["modules"][1]["lesson_count"] == 1
    assert tree[0]["modules"][0]["lessons"] == []
