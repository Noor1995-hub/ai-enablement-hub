"""promote "For Developers" to the multiplier level

Two coupled changes:
  - Widen the tracks.required_level CHECK to include 'multiplier' (the maturity
    ladder's aspirational top rung — previously only users.maturity_override
    accepted it; see b4e5f6a7c8d9).
  - Move the "For Developers" tool track from 'integrator' to 'multiplier', so it
    renders under the Multiplier header on /learning and unlocks only once a
    learner closes out every integrator track (progression reaches multiplier).

Hand-written (autogenerate diffs neither CHECK-constraint text nor data). The
data step is a plain UPDATE keyed on the real production id (db/baseline/data),
so it is idempotent and replays cleanly after a destructive Supabase re-seed:
b4e5f6a7c8d9 sets the track to 'integrator', this revision then promotes it.
Exposed as module constants so the migration-sanity test runs the shipped SQL.

Revision ID: d8e9f0a1b2c3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-15

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "d8e9f0a1b2c3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Real production id of the "For Developers" tool track (db/baseline/data/tracks.json).
FOR_DEVELOPERS_ID = "7ce46ab6-f619-4183-a592-2404e50b8c10"

PROMOTE_SQL = f"UPDATE tracks SET required_level = 'multiplier' WHERE id = '{FOR_DEVELOPERS_ID}'"
DEMOTE_SQL = f"UPDATE tracks SET required_level = 'integrator' WHERE id = '{FOR_DEVELOPERS_ID}'"


def upgrade() -> None:
    # Widen the CHECK first, then move the track (the UPDATE would violate the old
    # three-value constraint).
    op.drop_constraint(op.f("ck_tracks_required_level"), "tracks", type_="check")
    op.create_check_constraint(
        op.f("ck_tracks_required_level"),
        "tracks",
        "required_level IN ('explore', 'practitioner', 'integrator', 'multiplier')",
    )
    op.execute(PROMOTE_SQL)


def downgrade() -> None:
    # Move the track back first, then narrow the CHECK (a lingering 'multiplier'
    # row would fail the three-value constraint).
    op.execute(DEMOTE_SQL)
    op.drop_constraint(op.f("ck_tracks_required_level"), "tracks", type_="check")
    op.create_check_constraint(
        op.f("ck_tracks_required_level"),
        "tracks",
        "required_level IN ('explore', 'practitioner', 'integrator')",
    )
