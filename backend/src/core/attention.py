"""Pure attention rules for the admin panel (spec §4.4).

The single home of the "needs attention" logic, shared by the People directory
(``AdminUserService.list_users``) and the Dashboard (Task 10). Both import
``attention_for`` directly rather than one service calling the other — services
never call services. This module is deliberately pure: no I/O, no session, no
imports of repositories or services, so the rules stay unit-testable and have
exactly one definition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

__all__ = ["ACTIVE_DAYS", "NUDGE_DAYS", "STALLED_DAYS", "attention_for"]

STALLED_DAYS = 14  # locked, spec §4.4
ACTIVE_DAYS = 7  # locked, spec §4.4
NUDGE_DAYS = 7  # chosen default for "invited, never activated" / "activated, not assessed"


def attention_for(
    *,
    now: datetime,
    created_at: datetime,
    activated: bool,
    activated_known_since: datetime,
    has_survey: bool,
    latest_completion: datetime | None,
    assigned_total: int,
    completed_total: int,
    track_names_in_progress: list[str],
) -> tuple[str, str] | None:
    """Returns (kind, human reason) or None.

    kinds: 'never_activated' | 'not_assessed' | 'stalled'.

    Rules, in priority order:
    1. Not activated and invited >= NUDGE_DAYS ago -> never_activated.
    2. Activated, no survey row, and >= NUDGE_DAYS since activated_known_since
       -> not_assessed.
    3. Activated + assessed, still has unfinished assigned lessons
       (completed_total < assigned_total) and the last completion is older than
       STALLED_DAYS -> stalled (a never-started learner with no completion is
       not "stalled" — stalled means started then stopped).

    ``activated_known_since`` is an approximation: the ``users`` table has no
    "activated_at" column, so the caller passes max(created_at, first session's
    last_used_at) — the earliest moment we can prove the account was live.
    """
    if not activated:
        if (now - created_at).days >= NUDGE_DAYS:
            return ("never_activated", "Invited, never activated")
        return None

    if not has_survey:
        days = (now - activated_known_since).days
        if days >= NUDGE_DAYS:
            return ("not_assessed", f"Activated {days} days ago, assessment not started")
        return None

    if completed_total < assigned_total and latest_completion is not None:
        days = (now - latest_completion).days
        if days > STALLED_DAYS:
            if track_names_in_progress:
                return ("stalled", f"Stalled in {track_names_in_progress[0]} for {days} days")
            return ("stalled", f"Stalled for {days} days")

    return None
