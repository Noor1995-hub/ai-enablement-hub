"""Tracks and modules get the deferred sort_order uniqueness lessons already
have (migration b0c1d2e3f4a5, spec 2026-10-05). Deferred: a permutation may
pass through duplicates mid-transaction; the check runs at commit. This
harness never really commits (savepoints), so tests force the check with
SET CONSTRAINTS ... IMMEDIATE, as test_lesson_sort_order_uniqueness.py does."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.db.models import Module, Track
from tests.fixtures.factories import create_module, create_track

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "alembic"
    / "versions"
    / "b0c1d2e3f4a5_unique_track_module_sort_order.py"
)


def _migration():  # noqa: ANN202 - a loaded module
    spec = importlib.util.spec_from_file_location("b0c1d2e3f4a5", _MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def test_two_tracks_cannot_share_a_sort_order(db_session: AsyncSession) -> None:
    await create_track(db_session, "A", sort_order=7)
    db_session.add(Track(name="B", track_type="general", required_level="explore", sort_order=7))
    await db_session.flush()
    with pytest.raises(IntegrityError):
        await db_session.execute(text("SET CONSTRAINTS uq_tracks_sort_order IMMEDIATE"))
    await db_session.rollback()


async def test_two_modules_in_one_track_cannot_share_a_sort_order(
    db_session: AsyncSession,
) -> None:
    track = await create_track(db_session, "T")
    await create_module(db_session, track, "M1", sort_order=3)
    db_session.add(Module(track_id=track.id, title="M2", sort_order=3))
    await db_session.flush()
    with pytest.raises(IntegrityError):
        await db_session.execute(text("SET CONSTRAINTS uq_modules_track_id_sort_order IMMEDIATE"))
    await db_session.rollback()


async def test_factories_pick_the_next_free_sort_order(db_session: AsyncSession) -> None:
    first = await create_track(db_session, "First")
    second = await create_track(db_session, "Second")
    assert second.sort_order == first.sort_order + 1
    m1 = await create_module(db_session, first, "M1")
    m2 = await create_module(db_session, first, "M2")
    assert (m1.sort_order, m2.sort_order) == (0, 1)


async def test_renumbering_keeps_the_sort_order_then_id_order(db_session: AsyncSession) -> None:
    """The migration's data step on tied rows: inside one transaction the
    deferred constraint lets us create the live-data shape (a tie), then the
    renumber must produce 0..n-1 in (sort_order, id) order."""
    migration = _migration()
    rows = [
        Track(name=name, track_type="general", required_level="explore", sort_order=order)
        for name, order in (("tie-a", 5), ("tie-b", 5), ("low", 2))
    ]
    db_session.add_all(rows)
    await db_session.flush()
    expected = [t.id for t in sorted(rows, key=lambda t: (t.sort_order, str(t.id)))]

    await db_session.execute(text(migration.RENUMBER_TRACKS_SQL))
    await db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    result = await db_session.execute(
        text("SELECT id FROM tracks WHERE name IN ('tie-a','tie-b','low') ORDER BY sort_order")
    )
    assert [row[0] for row in result.all()] == expected
