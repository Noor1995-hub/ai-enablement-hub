"""lesson content proposals — the AI content-improvement draft store

One row per drafted revision of a lesson's content_blocks: the proposal
itself, a snapshot of the blocks it was drafted against (so the review diff
is stable and a stale proposal is detectable), the accepted feedback ids that
drove it, the agent's summary, and a review status.

Purely additive: a new table, no change to `lessons` or `feedback`. Nothing
reads it until an admin triggers a run, so deploying this ahead of use is
inert.

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-07-28

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e8f9a0b1c2d3"
down_revision: str | None = "d7e8f9a0b1c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lesson_content_proposals",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("lesson_id", sa.UUID(), nullable=False),
        sa.Column("proposed_blocks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("base_blocks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_feedback_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected','superseded','failed')",
            name=op.f("ck_lesson_content_proposals_status"),
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_lesson_content_proposals_lesson_id_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name=op.f("fk_lesson_content_proposals_reviewed_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lesson_content_proposals")),
    )
    op.create_index(
        op.f("ix_lesson_content_proposals_lesson_id"),
        "lesson_content_proposals",
        ["lesson_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_lesson_content_proposals_lesson_id"),
        table_name="lesson_content_proposals",
    )
    op.drop_table("lesson_content_proposals")
