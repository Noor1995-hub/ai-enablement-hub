"""index the FK columns we join and cascade on

`feedback.user_id` was the load-bearing gap: deleting a user cascaded through a
seq-scan of `feedback`, and the project-scoped admin feedback queue joins
`users` to filter on `project_id`. The three `ON DELETE SET NULL` audit columns
(`feedback.reviewed_by`, `lesson_content_proposals.reviewed_by`,
`calibration_notes.reviewed_by`) had the same problem on a smaller scale — a
user delete had to seq-scan each of them.

`prompts.updated_by` is deliberately NOT indexed here even though it has the
same shape: the `prompts` table is being dropped by a later phase-C migration
(prompts are git-only since PR #16), so indexing a column on a table about to
be dropped would be wasted work and complicate that migration's downgrade
ordering.

Purely additive: four B-tree indexes, no row is read or written. All tables
are small (hundreds of rows), so each CREATE INDEX is a millisecond-scale
operation. Migrations are applied only by the Deploy workflow's migrate job
(not on container start), and this one is expand-first: an older image keeps
working unchanged against the new schema.

Revision ID: a1b2c3d4e5f6
Revises: 1cd2cc2d05a9
Create Date: 2026-09-29

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "1cd2cc2d05a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (index name, table, column) — names match the metadata naming convention's
# `ix_%(column_0_label)s`, i.e. what `index=True` on the model column produces.
_INDEXES = (
    ("ix_feedback_user_id", "feedback", "user_id"),
    ("ix_feedback_reviewed_by", "feedback", "reviewed_by"),
    (
        "ix_lesson_content_proposals_reviewed_by",
        "lesson_content_proposals",
        "reviewed_by",
    ),
    ("ix_calibration_notes_reviewed_by", "calibration_notes", "reviewed_by"),
)


def upgrade() -> None:
    for name, table, column in _INDEXES:
        op.create_index(op.f(name), table, [column], unique=False)


def downgrade() -> None:
    for name, table, _column in reversed(_INDEXES):
        op.drop_index(op.f(name), table_name=table)
