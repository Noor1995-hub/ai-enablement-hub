"""maturity-gated learning path

Adds the maturity ladder over the learning path:
  - tracks.required_level (General I → explore, General II → practitioner, all
    tool tracks → integrator) — the level a user must reach for a track to unlock.
  - users.maturity_override — the admin maturity pin (base of the live effective
    level; NULL = from the assessment).
  - Restructures the single "General" track into "General I" (explore, first 5
    modules) + a new "General II" (practitioner, the last 3 modules), shifting
    the tool tracks' sort_order down by one. The cross-track boundary prereq
    (Integrating ← Using AI safely) is deliberately kept.

Hand-written (autogenerate diffs neither CHECK-constraint text nor data). Every
step is idempotent and guarded so a destructive Supabase re-seed can replay it
via `alembic downgrade -1 && alembic upgrade head` (see db/README.md): the seed
reloads the PRE-split baseline, and this revision restructures on top.

Revision ID: b4e5f6a7c8d9
Revises: c7d2e9f0a1b3
Create Date: 2026-07-08

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b4e5f6a7c8d9"
down_revision: str | None = "c7d2e9f0a1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The live "General" track (becomes "General I"); its last 3 modules move to a
# new deterministic "General II". These UUIDs are the real production ids (see
# db/baseline/data/) — literals so the migration is data-driven and re-runnable.
GENERAL_I_ID = "1a810a92-dce9-4f6f-88e6-b73d63cf65fa"
GENERAL_II_ID = "f7e6d5c4-b3a2-4190-8f00-0000000000e2"
GENERAL_II_MODULE_IDS = (
    "8a22da4a-0ce3-4d8f-8713-c5a6ab7082bb",  # Integrating AI into your work (sort 60)
    "e2202cbc-e26f-4ed6-a178-27fcdd85abce",  # Apply it: your first AI-assisted task (sort 70)
    "4e9f8450-5bbe-47f8-a014-ce3cc41f19d0",  # From foundation to tools (sort 80)
)
_MOVE_IDS = "'{}', '{}', '{}'".format(*GENERAL_II_MODULE_IDS)

# Populate required_level for existing tracks (idempotent — only NULLs). Tool
# tracks gate on Integrator; every general track defaults to Explorer (General II
# is bumped to Practitioner when it is created by RESTRUCTURE_SQL).
POPULATE_SQL = """
    UPDATE tracks
    SET required_level = CASE WHEN track_type = 'tool' THEN 'integrator' ELSE 'explore' END
    WHERE required_level IS NULL
"""

# Split General → General I + General II. Guarded on General II's absence so a
# replay (or a fresh/empty DB) never double-shifts or double-inserts. Exposed as
# a module constant so the migration-sanity test runs the exact shipped SQL.
RESTRUCTURE_SQL = f"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM tracks WHERE name = 'General II') THEN
            -- General I: rename + fix ordering (required_level already 'explore').
            UPDATE tracks SET name = 'General I', sort_order = 0 WHERE id = '{GENERAL_I_ID}';

            -- Make room at sort_order 1 for General II.
            UPDATE tracks SET sort_order = sort_order + 1 WHERE track_type = 'tool';

            -- General II (Practitioner), inheriting General I's colour.
            INSERT INTO tracks (id, name, sort_order, track_type, color, required_level)
            SELECT '{GENERAL_II_ID}', 'General II', 1, 'general', color, 'practitioner'
            FROM tracks WHERE id = '{GENERAL_I_ID}';

            -- Move the last 3 General modules to General II (ids/sort_order kept, so
            -- assignments/lessons/progress are untouched).
            UPDATE modules SET track_id = '{GENERAL_II_ID}' WHERE id IN ({_MOVE_IDS});
            -- The boundary prereq (Integrating ← Using AI safely) is intentionally kept:
            -- it becomes a cross-track edge (General II depends on General I), enforced
            -- but not drawn (pre-existing cross-track pattern).
        END IF;
    END $$
"""

UNSPLIT_SQL = f"""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM tracks WHERE id = '{GENERAL_II_ID}') THEN
            UPDATE modules SET track_id = '{GENERAL_I_ID}' WHERE id IN ({_MOVE_IDS});
            DELETE FROM tracks WHERE id = '{GENERAL_II_ID}';
            UPDATE tracks SET sort_order = sort_order - 1 WHERE track_type = 'tool';
            UPDATE tracks SET name = 'General' WHERE id = '{GENERAL_I_ID}';
        END IF;
    END $$
"""


def upgrade() -> None:
    # 1. New columns, nullable first so existing rows survive the add.
    op.add_column("tracks", sa.Column("required_level", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("maturity_override", sa.Text(), nullable=True))

    # 2. Populate required_level, then 3. split General → General I + General II.
    op.execute(POPULATE_SQL)
    op.execute(RESTRUCTURE_SQL)

    # 4. Lock the column down and add the CHECK constraints (naming-convention names).
    op.alter_column("tracks", "required_level", nullable=False)
    op.create_check_constraint(
        op.f("ck_tracks_required_level"),
        "tracks",
        "required_level IN ('explore', 'practitioner', 'integrator')",
    )
    op.create_check_constraint(
        op.f("ck_users_maturity_override"),
        "users",
        "maturity_override IN ('explore', 'practitioner', 'integrator', 'multiplier')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_users_maturity_override"), "users", type_="check")
    op.drop_constraint(op.f("ck_tracks_required_level"), "tracks", type_="check")
    op.execute(UNSPLIT_SQL)
    op.drop_column("users", "maturity_override")
    op.drop_column("tracks", "required_level")
