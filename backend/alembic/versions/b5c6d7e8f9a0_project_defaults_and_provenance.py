"""project defaults and assignment provenance

Revision ID: b5c6d7e8f9a0
Revises: 12bf5f54a1e4
Create Date: 2026-07-23

Re-parented 2026-07-27 onto Matthias's chat-foundation migration (12bf5f54a1e4),
which the shared dev DB already had applied. Both originally chained off
e2f3a4b5c6d7; single-chain policy — this branch merged second, so it re-parents.

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "b5c6d7e8f9a0"
down_revision: str | None = "12bf5f54a1e4"
branch_labels = None
depends_on = None

_ASSIGNMENT_TABLES = ("user_tracks", "user_modules", "user_lessons")


def upgrade() -> None:
    op.create_table(
        "project_track_defaults",
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("track_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_track_defaults_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["track_id"],
            ["tracks.id"],
            name=op.f("fk_project_track_defaults_track_id_tracks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id", "track_id", name=op.f("pk_project_track_defaults")),
    )
    op.create_index(
        op.f("ix_project_track_defaults_track_id"),
        "project_track_defaults",
        ["track_id"],
        unique=False,
    )
    for table in _ASSIGNMENT_TABLES:
        op.add_column(
            table,
            sa.Column(
                "assigned_via", sa.Text(), server_default=sa.text("'manual'"), nullable=False
            ),
        )
        op.create_check_constraint(
            op.f(f"ck_{table}_assigned_via"), table, "assigned_via IN ('manual','default')"
        )


def downgrade() -> None:
    for table in _ASSIGNMENT_TABLES:
        op.drop_constraint(op.f(f"ck_{table}_assigned_via"), table, type_="check")
        op.drop_column(table, "assigned_via")
    op.drop_index(op.f("ix_project_track_defaults_track_id"), table_name="project_track_defaults")
    op.drop_table("project_track_defaults")
