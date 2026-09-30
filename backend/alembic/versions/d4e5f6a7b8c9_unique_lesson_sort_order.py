"""unique (module_id, sort_order) on lessons — DEFERRABLE

Review finding 6.5. Ties (both `create_lesson` and `create_module` assign
`max(sort_order)+1`, so a lost race between two concurrent creates can
duplicate it) made lesson ordering non-deterministic; the read-side fix
already shipped in a separate phase-C task. This closes the write side for
lessons only.

Verified against prod (progress.md, read-only, 2026-09-29): 0 rows with a
duplicate (module_id, sort_order) among lessons, so this constraint validates
cleanly. Modules and tracks are NOT covered here: prod has 2 duplicate
(track_id, sort_order) pairs among modules and 1 duplicate sort_order among
tracks, so the equivalent constraint on those tables would raise and stop the
migrate job; that is a data-normalisation decision for someone else, not this
task.

DEFERRABLE INITIALLY DEFERRED is required, not optional: reordering a
module's lessons (ContentRepository.set_lesson_orders) writes each lesson's
new sort_order in its own UPDATE statement, so a permutation passes through
intermediate states where two lessons briefly share a value. A plain (non-
deferrable) unique index would break that reorder.

Live data: adds one unique constraint, validated at creation against
existing rows (clean per the census above). The table is small, so this runs
in well under the migrate job's budget. Migrations are applied only by the
Deploy workflow's migrate job, and this is expand-first: an older image
keeps working unchanged against the new schema (it doesn't rely on the
constraint, so it can't violate it).

Side effect worth flagging: two concurrent admin lesson creates into the same
module (both computing `max(sort_order)+1` from the same value) now 500 the
loser at COMMIT instead of silently producing two lessons with the same
sort_order.

Reversible without loss (downgrade drops the constraint).

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7
Create Date: 2026-09-29

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        op.f("uq_lessons_module_id_sort_order"),
        "lessons",
        ["module_id", "sort_order"],
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_lessons_module_id_sort_order"), "lessons", type_="unique")
