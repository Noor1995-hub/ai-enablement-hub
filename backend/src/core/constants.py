"""Server-side home of the component constants (was app/api/_lib/constants.js)
and the shared pure progress rules (level ordering, the ladder walk, and the
map it walks).

Moving these behind the API kills the old D4 duplication: the frontend now
receives resolved hidden/locked flags from /me/journey and the admin component
endpoints instead of re-deriving defaults itself.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "COMPONENTS",
    "DEFAULT_HIDDEN",
    "DEFAULT_LOCKED",
    "LEVEL_ORDER",
    "LEVEL_RANK",
    "advance_level",
    "module_level_map",
]

COMPONENTS = ("assessment", "learning", "interview")
DEFAULT_LOCKED = {"assessment": False, "learning": True, "interview": True}
DEFAULT_HIDDEN = {"assessment": False, "learning": False, "interview": False}

# The maturity ladder, in progression order. The scoring engine only ever
# assigns the first three (`multiplier` is aspirational — see lib/levels.ts on
# the frontend), but an admin override may pin any of the four. This is the
# single server-side source of truth for level ordering and `next_level`.
LEVEL_ORDER = ("explore", "practitioner", "integrator", "multiplier")
LEVEL_RANK = {code: index for index, code in enumerate(LEVEL_ORDER)}


def next_level(level: str) -> str | None:
    """The level one rung above `level`, or None at the top of the ladder."""
    rank = LEVEL_RANK.get(level)
    if rank is None or rank + 1 >= len(LEVEL_ORDER):
        return None
    return LEVEL_ORDER[rank + 1]


class _HasRequiredLevel(Protocol):
    """Structural stand-in for `db.models.Track`. Typed structurally so `core/`
    stays free of any `src.db` import (it imports nothing from src today) while
    `ty` still checks the two attributes this function reads."""

    @property
    def id(self) -> uuid.UUID: ...
    @property
    def required_level(self) -> str: ...


class _HasTrackId(Protocol):
    """Structural stand-in for `db.models.Module`."""

    @property
    def id(self) -> uuid.UUID: ...
    @property
    def track_id(self) -> uuid.UUID: ...


def module_level_map(
    tracks: Sequence[_HasRequiredLevel], modules: Sequence[_HasTrackId]
) -> dict[uuid.UUID, str]:
    """module_id -> the required_level of the track it belongs to.

    The input `advance_level` walks, and the single definition of it: this was
    copy-defined in MaturityService (the learner graph), AdminUserService (the
    admin directory) and DashboardService (the admin dashboard), which is how the
    third copy got written after prior audit 4.3 shared only the ladder walk.

    A module whose `track_id` is not among `tracks` is SKIPPED, not an error —
    preserving all three copies' `if module.track_id in track_level` guard. Such a
    module simply never gates a level.
    """
    track_level = {track.id: track.required_level for track in tracks}
    return {
        module.id: track_level[module.track_id]
        for module in modules
        if module.track_id in track_level
    }


def advance_level(
    base: str,
    module_level: dict[uuid.UUID, str],
    counts: dict[uuid.UUID, tuple[int, int]],
) -> str:
    """Walk the maturity ladder up from `base`, advancing one rung while every
    module the user has assigned lessons for at the current level is complete.
    Pure: `module_level` maps module_id → its track's required_level, `counts`
    maps module_id → (assigned lessons, assigned-and-completed lessons). The
    single source of truth for effective maturity, shared by MaturityService
    (the learner graph) and AdminUserService (the admin directory) so neither
    imports the other."""
    level = base
    while (nxt := next_level(level)) is not None:
        # Modules at this level the user actually has assigned lessons for — a
        # level clears over the content the user has, never vacuously.
        assigned = [
            mid
            for mid, lvl in module_level.items()
            if lvl == level and counts.get(mid, (0, 0))[0] > 0
        ]
        if not assigned:
            break
        if all(counts[mid][1] == counts[mid][0] for mid in assigned):
            level = nxt
        else:
            break
    return level
