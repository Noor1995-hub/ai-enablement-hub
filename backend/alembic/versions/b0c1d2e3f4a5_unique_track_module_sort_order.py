"""unique sort_order on tracks and on modules per track: DEFERRABLE (B4)

Spec: docs/superpowers/specs/2026-10-05-content-structure-editing-design.md.
Live data has duplicate sort_order values on tracks and on (track_id,
sort_order) for modules (see d4e5f6a7b8c9, which constrained lessons only).

1. Renumber both to 0..n-1 in (sort_order, id) order: the order every query
   already uses (content_repository.py: order_by(sort_order, id)), so
   learners see nothing move.
2. Add deferrable, initially deferred unique constraints, like lessons'.

Expand-first: the running image keeps working. create_track appends max+1;
create_module's "shift successors +1, then insert" only collides
mid-transaction, which a deferred constraint allows.

Downgrade drops the constraints; the renumbering is not undone (harmless:
relative order is unchanged).

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "b0c1d2e3f4a5"
down_revision: str | None = "a9b0c1d2e3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RENUMBER_TRACKS_SQL = """
UPDATE tracks AS t SET sort_order = r.rn
FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY sort_order, id) - 1 AS rn FROM tracks) AS r
WHERE t.id = r.id AND t.sort_order IS DISTINCT FROM r.rn
"""

RENUMBER_MODULES_SQL = """
UPDATE modules AS m SET sort_order = r.rn
FROM (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY track_id ORDER BY sort_order, id) - 1 AS rn
    FROM modules
) AS r
WHERE m.id = r.id AND m.sort_order IS DISTINCT FROM r.rn
"""


def upgrade() -> None:
    op.execute(RENUMBER_TRACKS_SQL)
    op.execute(RENUMBER_MODULES_SQL)
    op.create_unique_constraint(
        op.f("uq_tracks_sort_order"),
        "tracks",
        ["sort_order"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_unique_constraint(
        op.f("uq_modules_track_id_sort_order"),
        "modules",
        ["track_id", "sort_order"],
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_modules_track_id_sort_order"), "modules", type_="unique")
    op.drop_constraint(op.f("uq_tracks_sort_order"), "tracks", type_="unique")
