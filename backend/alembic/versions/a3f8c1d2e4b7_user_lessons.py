"""user_lessons — per-lesson assignment

Lesson assignment mirrors user_modules: an admin now assigns individual
lessons of an assigned module to a user. Backfills all lessons of every
existing (user, module) assignment so current learners keep exactly what
they see today; module assignments made after this start with no lessons
(the admin picks them, or uses the "Add all lessons" button).

Revision ID: a3f8c1d2e4b7
Revises: 5cd94241caf6
Create Date: 2026-07-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a3f8c1d2e4b7"
down_revision: str | None = "5cd94241caf6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_lessons",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("lesson_id", sa.UUID(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            name=op.f("fk_user_lessons_lesson_id_lessons"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_lessons_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_lessons")),
        sa.UniqueConstraint("user_id", "lesson_id", name=op.f("uq_user_lessons_user_id_lesson_id")),
    )
    op.create_index(op.f("ix_user_lessons_lesson_id"), "user_lessons", ["lesson_id"], unique=False)
    op.execute(
        """
        INSERT INTO user_lessons (user_id, lesson_id)
        SELECT um.user_id, l.id
        FROM user_modules um
        JOIN lessons l ON l.module_id = um.module_id
        ON CONFLICT (user_id, lesson_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_lessons_lesson_id"), table_name="user_lessons")
    op.drop_table("user_lessons")
