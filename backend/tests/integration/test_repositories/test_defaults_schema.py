from __future__ import annotations

import uuid

from sqlalchemy import select

from src.db.models import ProjectTrackDefault, UserTrack
from tests.fixtures.factories import create_company, create_project, create_track, create_user


async def test_project_track_default_roundtrip(db_session) -> None:
    company = await create_company(db_session)
    project = await create_project(db_session, company)
    track = await create_track(db_session)
    db_session.add(ProjectTrackDefault(project_id=project.id, track_id=track.id))
    await db_session.commit()
    row = (await db_session.execute(select(ProjectTrackDefault))).scalar_one()
    assert (row.project_id, row.track_id) == (project.id, track.id)


async def test_assigned_via_defaults_to_manual(db_session) -> None:
    user = await create_user(db_session, email=f"{uuid.uuid4()}@x.test")
    track = await create_track(db_session)
    db_session.add(UserTrack(user_id=user.id, track_id=track.id))
    await db_session.commit()
    row = (await db_session.execute(select(UserTrack))).scalar_one()
    assert row.assigned_via == "manual"
