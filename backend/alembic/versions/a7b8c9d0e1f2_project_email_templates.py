"""project_email_templates — per-project invite/reset email overrides

One row per (project, purpose in {invite, reset}); absent rows fall back to the
code-level DEFAULT_TEMPLATES. CASCADE on the project FK so a deleted project
takes its overrides with it. Hand-written CHECK/UNIQUE names match the metadata
naming convention.

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-07-14

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_email_templates",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "purpose IN ('invite', 'reset')",
            name=op.f("ck_project_email_templates_purpose"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_email_templates_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_email_templates")),
        sa.UniqueConstraint(
            "project_id",
            "purpose",
            name=op.f("uq_project_email_templates_project_id_purpose"),
        ),
    )


def downgrade() -> None:
    op.drop_table("project_email_templates")
