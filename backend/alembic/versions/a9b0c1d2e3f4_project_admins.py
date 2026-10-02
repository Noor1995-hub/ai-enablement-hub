"""project admins; drop the "user+" role

Adds project_admins (user_id, project_id) — a 'user' with rows here administers
exactly those projects; role 'admin' stays the (power) admin. "user+" is dropped:
its rows become 'user' and the role CHECK narrows to ('admin', 'user').
Spec: docs/superpowers/specs/2026-10-01-project-scoped-admin-design.md.

Downgrade drops the table and widens the CHECK again; former user+ accounts are
not restored (accepted in the spec — the role only bypassed locks).

Revision ID: a9b0c1d2e3f4
Revises: f9c9852f6362
Create Date: 2026-10-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a9b0c1d2e3f4"
down_revision: str | None = "f9c9852f6362"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_admins",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_project_admins_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_admins_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.id"],
            name=op.f("fk_project_admins_granted_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("user_id", "project_id", name=op.f("pk_project_admins")),
    )
    op.create_index(op.f("ix_project_admins_project_id"), "project_admins", ["project_id"])
    op.create_index(op.f("ix_project_admins_granted_by"), "project_admins", ["granted_by"])

    op.execute("UPDATE users SET role = 'user' WHERE role = 'user+'")
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.create_check_constraint(op.f("ck_users_role"), "users", "role IN ('admin', 'user')")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.create_check_constraint(op.f("ck_users_role"), "users", "role IN ('admin', 'user+', 'user')")
    op.drop_index(op.f("ix_project_admins_granted_by"), table_name="project_admins")
    op.drop_index(op.f("ix_project_admins_project_id"), table_name="project_admins")
    op.drop_table("project_admins")
