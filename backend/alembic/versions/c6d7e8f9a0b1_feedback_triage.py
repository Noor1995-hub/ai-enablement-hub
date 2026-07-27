"""feedback triage — status columns + admin queue endpoints

Adds a triage workflow to feedback rows: status (new/accepted/dismissed,
defaulting to 'new' for existing rows), plus reviewed_at/reviewed_by so the
admin queue can show who actioned a piece of feedback and when.
reviewed_by is nullable and ON DELETE SET NULL so deleting the reviewing
admin never blocks or cascades into deleting feedback history.

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-07-23

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c6d7e8f9a0b1"
down_revision: str | None = "b5c6d7e8f9a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "feedback",
        sa.Column("status", sa.Text(), server_default=sa.text("'new'"), nullable=False),
    )
    op.add_column("feedback", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("feedback", sa.Column("reviewed_by", sa.UUID(), nullable=True))
    op.create_check_constraint(
        op.f("ck_feedback_status"), "feedback", "status IN ('new','accepted','dismissed')"
    )
    op.create_foreign_key(
        op.f("fk_feedback_reviewed_by_users"),
        "feedback",
        "users",
        ["reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_feedback_reviewed_by_users"), "feedback", type_="foreignkey")
    op.drop_constraint(op.f("ck_feedback_status"), "feedback", type_="check")
    op.drop_column("feedback", "reviewed_by")
    op.drop_column("feedback", "reviewed_at")
    op.drop_column("feedback", "status")
