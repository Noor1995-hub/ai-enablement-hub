"""Introduction pseudo-level (2026-07-17): the mandatory pre-Explorer track.

Covers the shipped migration SQL, the graph's implicit assignment + force-unlock,
the intro-lesson-assigned lesson endpoints, and the survey seed skipping it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import select, text

from src.db.models import Track

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


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
