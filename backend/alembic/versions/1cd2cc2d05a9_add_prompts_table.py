"""add prompts table

Revision ID: 1cd2cc2d05a9
Revises: f9a0b1c2d3e4
Create Date: 2026-07-30 08:33:06.805796

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "1cd2cc2d05a9"
down_revision: str | None = "f9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prompts",
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name=op.f("fk_prompts_updated_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("kind", name=op.f("pk_prompts")),
    )


def downgrade() -> None:
    op.drop_table("prompts")
