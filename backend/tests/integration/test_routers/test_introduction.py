"""Introduction pseudo-level (2026-07-17): the mandatory pre-Explorer track.

Covers the shipped migration SQL, the graph's implicit assignment + force-unlock,
the intro-lesson-assigned lesson endpoints, and the survey seed skipping it.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest_asyncio
from sqlalchemy import select, text

from src.db.models import Track
from tests.fixtures.auth import auth_headers
from tests.fixtures.factories import (
    create_lesson,
    create_module,
    create_track,
    create_user,
)

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.configs.settings import Settings
    from src.db.models import Lesson, Module, User


def _load_introduction_sql() -> str:
    # `import alembic...` would resolve to the installed alembic *package*
    # (site-packages), not this repo's `backend/alembic/` directory — alembic's
    # `versions/` has no `__init__.py` either, so it isn't an importable
    # subpackage. Load the migration module straight from its file path instead
    # (same pattern as test_maturity.py's `_load_restructure_sql`).
    path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "f3a4b5c6d7e8_introduction_track.py"
    )
    spec = importlib.util.spec_from_file_location("_introduction_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.INTRODUCTION_SQL


class TestIntroductionMigration:
    async def test_migration_sql_inserts_introduction_track(self, db_session: AsyncSession) -> None:
        introduction_sql = _load_introduction_sql()

        await db_session.execute(text(introduction_sql))
        await db_session.flush()

        track = (
            await db_session.execute(select(Track).where(Track.is_introduction.is_(True)))
        ).scalar_one()
        assert track.name == "Introduction"
        assert track.required_level == "explore"
        assert track.track_type == "general"
        assert track.color == "#941914"
        assert track.sort_order == 0


@dataclass
class IntroWorld:
    intro: Track
    intro_mod: Module
    intro_lessons: list[Lesson]
    explore: Track
    explore_mod: Module
    learner: User  # no survey → no maturity


@pytest_asyncio.fixture
async def introworld(db_session: AsyncSession) -> IntroWorld:
    intro = await create_track(db_session, "Introduction", is_introduction=True, sort_order=0)
    intro_mod = await create_module(db_session, intro, "Welcome", sort_order=0)
    intro_lessons = [
        await create_lesson(db_session, intro_mod, f"I{i}", sort_order=i) for i in range(2)
    ]
    explore = await create_track(db_session, "General I", sort_order=1, required_level="explore")
    explore_mod = await create_module(db_session, explore, "GI Module", sort_order=0)
    await create_lesson(db_session, explore_mod, "GI L0", sort_order=0)
    # Learner has NO survey (no maturity) and NO assignment rows at all.
    learner = await create_user(db_session, email="intro-learner@example.com")
    return IntroWorld(intro, intro_mod, intro_lessons, explore, explore_mod, learner)


def _tracks(graph: dict) -> dict[str, dict]:
    return {t["id"]: t for t in graph["tracks"]}


def _modules(graph: dict) -> dict[str, dict]:
    return {m["id"]: m for m in graph["modules"]}


class TestIntroductionGraph:
    async def test_intro_implicitly_assigned_and_force_unlocked_without_maturity(
        self, client: AsyncClient, introworld: IntroWorld, test_settings: Settings
    ) -> None:
        graph = (
            await client.get(
                "/api/learning/graph",
                headers=auth_headers(introworld.learner, test_settings),
            )
        ).json()
        assert graph["maturity_level"] is None  # no survey
        tracks = _tracks(graph)
        intro = tracks[str(introworld.intro.id)]
        assert intro["is_introduction"] is True
        assert intro["assigned"] is True  # implicit, despite no user_tracks row
        assert intro["unlocked_by_maturity"] is True  # force-unlocked even w/o maturity
        # A non-intro explore track is NOT force-unlocked for a no-maturity user.
        assert tracks[str(introworld.explore.id)]["is_introduction"] is False
        assert tracks[str(introworld.explore.id)]["unlocked_by_maturity"] is False

    async def test_intro_module_counts_cover_all_lessons(
        self, client: AsyncClient, introworld: IntroWorld, test_settings: Settings
    ) -> None:
        graph = (
            await client.get(
                "/api/learning/graph",
                headers=auth_headers(introworld.learner, test_settings),
            )
        ).json()
        mod = _modules(graph)[str(introworld.intro_mod.id)]
        assert mod["is_introduction"] is True
        assert mod["assigned"] is True
        assert mod["lesson_count"] == 2  # ALL lessons, not just assigned
        assert mod["completed_lesson_count"] == 0
