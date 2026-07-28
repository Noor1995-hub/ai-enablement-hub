"""inline draft edits + learn cards

Adds four nullable columns to `lesson_content_proposals` so an admin can accept
an AI draft after changing it: `edited_blocks` holds what they actually
submitted (NULL = accepted exactly as drafted, i.e. nothing to learn), and the
three critique columns hold the agent's self-assessment of the difference.

Adds `calibration_notes`, one row per short piece of guidance the agent
suggested about its own drafting. Nothing reads these rows yet — the curation
UI and the prompt injection are a later plan — so deploying this ahead of use
is inert.

`source_proposal_id` is nullable ON DELETE SET NULL, not CASCADE: deleting a
lesson cascades through its proposals, and an approved note must outlive the
lesson it came from.

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-07-28

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f9a0b1c2d3e4"
down_revision: str | None = "e8f9a0b1c2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lesson_content_proposals",
        sa.Column("edited_blocks", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "lesson_content_proposals",
        sa.Column("critique_agent_wrong", sa.Text(), nullable=True),
    )
    op.add_column(
        "lesson_content_proposals",
        sa.Column("critique_admin_preferred", sa.Text(), nullable=True),
    )
    op.add_column(
        "lesson_content_proposals",
        sa.Column("critiqued_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "calibration_notes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_proposal_id", sa.UUID(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'suggested'"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "status IN ('suggested','approved','rejected','retired')",
            name=op.f("ck_calibration_notes_status"),
        ),
        sa.ForeignKeyConstraint(
            ["source_proposal_id"],
            ["lesson_content_proposals.id"],
            name=op.f("fk_calibration_notes_source_proposal_id_lesson_content_proposals"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name=op.f("fk_calibration_notes_reviewed_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calibration_notes")),
    )
    op.create_index(
        op.f("ix_calibration_notes_source_proposal_id"),
        "calibration_notes",
        ["source_proposal_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_calibration_notes_source_proposal_id"), table_name="calibration_notes")
    op.drop_table("calibration_notes")
    op.drop_column("lesson_content_proposals", "critiqued_at")
    op.drop_column("lesson_content_proposals", "critique_admin_preferred")
    op.drop_column("lesson_content_proposals", "critique_agent_wrong")
    op.drop_column("lesson_content_proposals", "edited_blocks")
