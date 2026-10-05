"""lessons.updated_at + lessons.updated_by (B5)

Spec: docs/superpowers/specs/2026-10-05-lesson-editor-qa-design.md. The lesson
editor's conflict check: a PATCH carrying an outdated updated_at is refused.

updated_at is added with server default now(), then backfilled to created_at
so existing lessons read as "unchanged since creation". updated_by is NULL for
every existing row (unknown).

Expand-first: the running image never reads or writes these columns, and the
server default fills updated_at on its inserts.

Downgrade drops both.

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-10-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b0c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.execute("UPDATE lessons SET updated_at = created_at")
    op.add_column(
        "lessons",
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_lessons_updated_by_users"),
        "lessons",
        "users",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_lessons_updated_by"), "lessons", ["updated_by"])


def downgrade() -> None:
    op.drop_index(op.f("ix_lessons_updated_by"), table_name="lessons")
    op.drop_constraint(op.f("fk_lessons_updated_by_users"), "lessons", type_="foreignkey")
    op.drop_column("lessons", "updated_by")
    op.drop_column("lessons", "updated_at")
