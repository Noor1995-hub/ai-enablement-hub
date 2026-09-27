"""Server-side home of the component constants (was app/api/_lib/constants.js).

Moving these behind the API kills the old D4 duplication: the frontend now
receives resolved hidden/locked flags from /me/journey and the admin component
endpoints instead of re-deriving defaults itself.
"""

from __future__ import annotations

import uuid

__all__ = [
    "COMPONENTS",
    "DEFAULT_HIDDEN",
    "DEFAULT_LOCKED",
    "LEVEL_ORDER",
    "LEVEL_RANK",
    "LOCK_BYPASS_ROLES",
    "advance_level",
]

COMPONENTS = ("assessment", "learning", "interview")
DEFAULT_LOCKED = {"assessment": False, "learning": True, "interview": True}
DEFAULT_HIDDEN = {"assessment": False, "learning": False, "interview": False}

# Roles that bypass learning-path locks (maturity + assignment). NOT a bypass of
# the project-level component locks: those are explicitly not a role check
# (see ComponentLockedError and the user+ role design doc). Also not the interview's
# assessment gate, which exempts admin only (core/dependencies/interview.py
# _ASSESSMENT_EXEMPT_ROLES).
LOCK_BYPASS_ROLES: tuple[str, ...] = ("admin", "user+")

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
