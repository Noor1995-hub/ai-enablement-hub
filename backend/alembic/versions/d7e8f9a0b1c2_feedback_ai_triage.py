"""feedback AI triage suggestion columns

Adds three nullable columns to `feedback` so an agent can pre-fill a SUGGESTED
disposition for the admin queue: ai_suggested_status ('accepted'|'dismissed'),
ai_rationale (the one-line reason shown to the admin) and ai_suggested_at
(NULL = no suggestion generated yet, which is what bounds a triage run).

All three are nullable and additive, so existing rows are untouched. The real
`status` column is deliberately NOT involved — an AI suggestion never changes
a feedback item's actual disposition.

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-07-28

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d7e8f9a0b1c2"
down_revision: str | None = "c6d7e8f9a0b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("feedback", sa.Column("ai_suggested_status", sa.Text(), nullable=True))
    op.add_column("feedback", sa.Column("ai_rationale", sa.Text(), nullable=True))
    op.add_column(
        "feedback", sa.Column("ai_suggested_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        op.f("ck_feedback_ai_suggested_status"),
        "feedback",
        "ai_suggested_status IS NULL OR ai_suggested_status IN ('accepted','dismissed')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_feedback_ai_suggested_status"), "feedback", type_="check")
    op.drop_column("feedback", "ai_suggested_at")
    op.drop_column("feedback", "ai_rationale")
    op.drop_column("feedback", "ai_suggested_status")
