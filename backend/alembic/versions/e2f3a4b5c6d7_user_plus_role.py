"""add the "user+" role

Widen the users.role CHECK from IN ('admin', 'user') to
IN ('admin', 'user+', 'user'). "user+" is a learner who bypasses every
learning-path lock (prerequisites, the Introduction gate, maturity gating) on
their assigned content, but holds no admin powers — require_admin still checks
role == 'admin', so /admin/* and lesson-edit endpoints 403 for a user+ exactly
as for a user. See docs/superpowers/specs/2026-07-22-user-plus-role-design.md.

Hand-written (autogenerate does not diff CHECK-constraint text). Downgrade
narrows the constraint back, so any lingering 'user+' row must first be demoted
to 'user' — the UPDATE guards the constraint recreation.

Revision ID: e2f3a4b5c6d7
Revises: f3a4b5c6d7e8
Create Date: 2026-07-22

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_role"),
        "users",
        "role IN ('admin', 'user+', 'user')",
    )


def downgrade() -> None:
    # Demote any user+ to a plain user before narrowing the CHECK (a lingering
    # 'user+' row would fail the two-value constraint).
    op.execute("UPDATE users SET role = 'user' WHERE role = 'user+'")
    op.drop_constraint(op.f("ck_users_role"), "users", type_="check")
    op.create_check_constraint(
        op.f("ck_users_role"),
        "users",
        "role IN ('admin', 'user')",
    )
