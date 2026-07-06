"""auth_tokens.purpose gains 'entra_login'

Entra ID sign-in delivers the token pair to the SPA via a one-time redeem
code stored in auth_tokens (same hashing/TTL machinery as invite/reset).
Hand-written: autogenerate does not diff CHECK constraint text.

Revision ID: c7d2e9f0a1b3
Revises: a3f8c1d2e4b7
Create Date: 2026-07-06

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "c7d2e9f0a1b3"
down_revision: str | None = "a3f8c1d2e4b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_auth_tokens_purpose"), "auth_tokens", type_="check")
    op.create_check_constraint(
        op.f("ck_auth_tokens_purpose"),
        "auth_tokens",
        "purpose IN ('invite', 'reset', 'entra_login')",
    )


def downgrade() -> None:
    # Login codes live 60 seconds; deleting stragglers is safe.
    op.execute("DELETE FROM auth_tokens WHERE purpose = 'entra_login'")
    op.drop_constraint(op.f("ck_auth_tokens_purpose"), "auth_tokens", type_="check")
    op.create_check_constraint(
        op.f("ck_auth_tokens_purpose"),
        "auth_tokens",
        "purpose IN ('invite', 'reset')",
    )
