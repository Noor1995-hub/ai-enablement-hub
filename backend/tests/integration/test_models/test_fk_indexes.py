"""Every FK column we join or cascade on must be indexed.

Asserted against the live test schema (built from `Base.metadata` by the
session `engine` fixture). Because the schema comes from the models, not from
replaying the migrations, this only proves the *model* declares the index —
not that the migration matches it. Migration-vs-model drift is caught
separately by CI's `migrations` job (`uv run alembic check` after upgrading a
throwaway database to head), not by this test.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import inspect

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

_EXPECTED = [
    ("feedback", "user_id"),
    ("feedback", "reviewed_by"),
    ("lesson_content_proposals", "reviewed_by"),
    ("calibration_notes", "reviewed_by"),
]


@pytest.mark.parametrize(("table", "column"), _EXPECTED)
async def test_fk_column_is_indexed(engine: AsyncEngine, table: str, column: str) -> None:
    async with engine.connect() as conn:
        indexes = await conn.run_sync(lambda sync: inspect(sync).get_indexes(table))
    indexed_leading_columns = {tuple(ix["column_names"][:1]) for ix in indexes}
    assert (column,) in indexed_leading_columns, (
        f"{table}.{column} has no index with it as the leading column; "
        f"found {sorted(indexed_leading_columns)}"
    )
