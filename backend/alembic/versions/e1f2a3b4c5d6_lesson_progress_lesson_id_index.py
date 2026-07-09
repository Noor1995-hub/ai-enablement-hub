"""index lesson_progress.lesson_id

lesson_progress was the only assignment child table whose content-side FK
(lesson_id) had no standalone index — its UniqueConstraint(user_id, lesson_id)
only covers user-leading lookups. Every lessons-delete cascade and every
"who completed lesson X" query therefore seq-scanned the table. This restores
parity with the sibling user_lessons table (which already indexes lesson_id).

Adding an index is non-destructive and safe on a populated table; it holds a
brief lock but lesson_progress is small.

Revision ID: e1f2a3b4c5d6
Revises: b4e5f6a7c8d9
Create Date: 2026-07-09

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "b4e5f6a7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_lesson_progress_lesson_id"), "lesson_progress", ["lesson_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_lesson_progress_lesson_id"), table_name="lesson_progress")
