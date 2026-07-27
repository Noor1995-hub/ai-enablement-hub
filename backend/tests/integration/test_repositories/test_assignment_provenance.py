from __future__ import annotations

import uuid

from sqlalchemy import select

from src.db.models import UserLesson, UserModule, UserTrack
from src.repositories.assignment_repository import AssignmentRepository
from tests.fixtures.factories import create_lesson, create_module, create_track, create_user


async def _track_provenance(db_session, user_id: uuid.UUID) -> str:
    row = (
        await db_session.execute(select(UserTrack).where(UserTrack.user_id == user_id))
    ).scalar_one()
    return row.assigned_via


async def _module_provenance(db_session, user_id: uuid.UUID) -> str:
    row = (
        await db_session.execute(select(UserModule).where(UserModule.user_id == user_id))
    ).scalar_one()
    return row.assigned_via


async def _lesson_provenance(db_session, user_id: uuid.UUID) -> str:
    row = (
        await db_session.execute(select(UserLesson).where(UserLesson.user_id == user_id))
    ).scalar_one()
    return row.assigned_via


# -- Tracks --


async def test_track_bulk_insert_carries_assigned_via(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    await repo.set_user_tracks(user.id, [track.id], True, assigned_via="default")
    assert await _track_provenance(db_session, user.id) == "default"


async def test_track_conflict_keeps_first_writer_provenance(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    await repo.set_user_track(user.id, track.id, True)  # manual first
    await repo.set_user_tracks(user.id, [track.id], True, assigned_via="default")  # apply later
    assert await _track_provenance(db_session, user.id) == "manual"


async def test_track_unassign_deletes_regardless_of_provenance(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    await repo.set_user_track(user.id, track.id, True, assigned_via="default")
    await repo.set_user_track(user.id, track.id, False)
    assert await repo.track_ids_for_user(user.id) == set()


# -- Modules --


async def test_module_bulk_insert_carries_assigned_via(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    await repo.set_user_modules(user.id, [module.id], True, assigned_via="default")
    assert await _module_provenance(db_session, user.id) == "default"


async def test_module_conflict_keeps_first_writer_provenance(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    await repo.set_user_module(user.id, module.id, True)  # manual first
    await repo.set_user_modules(user.id, [module.id], True, assigned_via="default")  # apply later
    assert await _module_provenance(db_session, user.id) == "manual"


async def test_module_unassign_deletes_regardless_of_provenance(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    await repo.set_user_module(user.id, module.id, True, assigned_via="default")
    await repo.set_user_module(user.id, module.id, False)
    assert await repo.module_ids_for_user(user.id) == set()


# -- Lessons --


async def test_lesson_bulk_insert_carries_assigned_via(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    lesson = await create_lesson(db_session, module)
    await repo.set_user_lessons(user.id, [lesson.id], True, assigned_via="default")
    assert await _lesson_provenance(db_session, user.id) == "default"


async def test_lesson_conflict_keeps_first_writer_provenance(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    lesson = await create_lesson(db_session, module)
    await repo.set_user_lesson(user.id, lesson.id, True)  # manual first
    await repo.set_user_lessons(user.id, [lesson.id], True, assigned_via="default")  # apply later
    assert await _lesson_provenance(db_session, user.id) == "manual"


async def test_lesson_unassign_deletes_regardless_of_provenance(db_session) -> None:
    repo = AssignmentRepository(db_session)
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    module = await create_module(db_session, track)
    lesson = await create_lesson(db_session, module)
    await repo.set_user_lesson(user.id, lesson.id, True, assigned_via="default")
    await repo.set_user_lesson(user.id, lesson.id, False)
    assert await repo.lesson_ids_for_user(user.id) == set()
