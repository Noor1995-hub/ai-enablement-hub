"""drop the retired prompts table

System prompts have been git-only since PR #16 (`f84fded`, spec
`2026-09-23-prompts-git-only-design.md`): nothing reads or writes this table,
and the spec scheduled its drop for phase C. This is that drop (C8b).

Data: the table held 0 rows at the 2026-09-23 census and again at the
2026-09-29 read-only check, so nothing is lost.

Rollback floor: after this deploys, rolling back (`image_sha`) to an image
built before `f84fded` fails at startup, because that image's lifespan
SELECTs `prompts` before binding the port. Any image at or after `f84fded`
is unaffected. Approved by Matthias on 2026-09-30.

Reversible: `downgrade()` re-creates the table exactly as `1cd2cc2d05a9` did
(empty; there is no data to restore).

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8
Create Date: 2026-09-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The primary key and the FK to users go with the table.
    op.drop_table("prompts")


def downgrade() -> None:
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
