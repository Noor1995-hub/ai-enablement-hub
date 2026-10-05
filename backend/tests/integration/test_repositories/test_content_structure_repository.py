"""B4 structure operations: each is one commit and leaves dense 0..n-1 order."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.assignment_repository import AssignmentRepository
from src.repositories.content_repository import ContentRepository
from tests.fixtures.factories import (
    assign_lesson,
    assign_module,
    complete_lesson,
    create_lesson,
    create_module,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def _orders(repo: ContentRepository, track_id) -> list[tuple[str, int]]:  # noqa: ANN001
    return [(m.title, m.sort_order) for m in await repo.list_modules(track_id)]


async def test_move_module_renumbers_both_tracks(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    source = await create_track(db_session, "Source")
    dest = await create_track(db_session, "Dest")
    a = await create_module(db_session, source, "A")
    await create_module(db_session, source, "B")
    await create_module(db_session, dest, "X")

    moved = await repo.move_module(a, dest.id)

    assert moved.track_id == dest.id
    assert await _orders(repo, source.id) == [("B", 0)]
    assert await _orders(repo, dest.id) == [("X", 0), ("A", 1)]


async def test_move_lesson_renumbers_both_modules(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    track = await create_track(db_session)
    m1 = await create_module(db_session, track, "M1")
    m2 = await create_module(db_session, track, "M2")
    l1 = await create_lesson(db_session, m1, "L1", sort_order=0)
    await create_lesson(db_session, m1, "L2", sort_order=1)
    await create_lesson(db_session, m2, "K1", sort_order=0)

    await repo.move_lesson(l1, m2.id)

    assert [(le.title, le.sort_order) for le in await repo.list_lessons(m1.id)] == [("L2", 0)]
    assert [(le.title, le.sort_order) for le in await repo.list_lessons(m2.id)] == [
        ("K1", 0),
        ("L1", 1),
    ]


async def test_delete_track_cascades_and_renumbers(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    first = await create_track(db_session, "First")
    doomed = await create_track(db_session, "Doomed")
    last = await create_track(db_session, "Last")
    module = await create_module(db_session, doomed, "M")
    await create_lesson(db_session, module, "L")

    await repo.delete_track(doomed)

    tracks = await repo.list_tracks()
    assert [t.sort_order for t in tracks] == list(range(len(tracks)))
    names = [t.name for t in tracks]
    assert names.index(first.name) < names.index(last.name)
    assert await repo.get_module(module.id) is None


async def test_delete_module_renumbers_its_track(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    track = await create_track(db_session)
    await create_module(db_session, track, "A")
    b = await create_module(db_session, track, "B")
    await create_module(db_session, track, "C")

    await repo.delete_module(b)

    assert await _orders(repo, track.id) == [("A", 0), ("C", 1)]


async def test_set_prerequisites_replaces_the_set(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    track = await create_track(db_session)
    a = await create_module(db_session, track, "A")
    b = await create_module(db_session, track, "B")
    c = await create_module(db_session, track, "C")
    await repo.set_prerequisites(c.id, [a.id])

    await repo.set_prerequisites(c.id, [b.id])

    pairs = {(p.module_id, p.prerequisite_module_id) for p in await repo.list_prerequisites()}
    assert (c.id, b.id) in pairs
    assert (c.id, a.id) not in pairs


async def test_learner_counts_for_lessons(db_session: AsyncSession) -> None:
    repo = ContentRepository(db_session)
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    lesson = await create_lesson(db_session, module)
    ann = await create_user(db_session, email="b4-count-ann@example.com")
    bob = await create_user(db_session, email="b4-count-bob@example.com")
    await assign_lesson(db_session, ann, lesson)
    await assign_lesson(db_session, bob, lesson)
    await complete_lesson(db_session, ann, lesson)

    assert await repo.learner_counts_for_lessons([lesson.id]) == (2, 1)
    assert await repo.learner_counts_for_lessons([]) == (0, 0)


async def test_gap_reads_and_pair_insert(db_session: AsyncSession) -> None:
    repo = AssignmentRepository(db_session)
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    old = await create_lesson(db_session, module, "Old", sort_order=0)
    new = await create_lesson(db_session, module, "New", sort_order=1)
    ann = await create_user(db_session, email="b4-gap-ann@example.com")
    await assign_module(db_session, ann, module)
    await assign_lesson(db_session, ann, old)

    assert await repo.user_ids_with_module(module.id) == {ann.id}
    inserted = await repo.add_user_lesson_pairs([(ann.id, new.id), (ann.id, old.id)])
    assert inserted == 1
    assert await repo.lesson_ids_for_user(ann.id) == {old.id, new.id}
    assert await repo.add_user_lesson_pairs([]) == 0
