# backend/tests/integration/test_repositories/test_content_repository.py
from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.content_repository import ContentRepository
from tests.fixtures.factories import create_module, create_track

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def test_next_module_in_track_is_tie_safe_on_sort_order(db_session: AsyncSession) -> None:
    """sort_order alone is not a total order: live data holds tracks with two
    modules sharing a sort_order (@20). "Next module" must still visit both
    instead of silently skipping whichever one sorts first."""
    track = await create_track(db_session, "Tie Track")
    module_a = await create_module(db_session, track, "Module A", sort_order=20)
    module_b = await create_module(db_session, track, "Module B", sort_order=20)
    module_c = await create_module(db_session, track, "Module C", sort_order=30)

    tied = sorted([module_a, module_b], key=lambda m: m.id)
    lower, higher = tied[0], tied[1]

    repo = ContentRepository(db_session)

    next_after_lower = await repo.next_module_in_track(track.id, lower.sort_order, lower.id)
    assert next_after_lower is not None
    assert next_after_lower.id == higher.id

    next_after_higher = await repo.next_module_in_track(track.id, higher.sort_order, higher.id)
    assert next_after_higher is not None
    assert next_after_higher.id == module_c.id

    next_after_c = await repo.next_module_in_track(track.id, module_c.sort_order, module_c.id)
    assert next_after_c is None
