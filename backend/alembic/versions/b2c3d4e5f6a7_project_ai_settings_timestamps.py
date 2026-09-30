"""add project_ai_settings.created_at/updated_at

project_ai_settings had neither timestamp while its sibling
project_component_settings already has `updated_at`. Review finding 6.4
(the `prompts` half of that finding is obsolete: prompts are git-only since
PR #16 and the table is dropped, not amended, by a later phase-C migration —
see the tail of the migration chain).

Live data: two additive `TIMESTAMPTZ NOT NULL DEFAULT now()` columns. Existing
rows are backfilled with this migration's timestamp — acceptable, since these
are settings/override rows whose creation time was never recorded. The table
is tiny (at most 4 rows per project), so this runs in milliseconds. Migrations
are applied only by the Deploy workflow's migrate job, and this is
expand-first: an older image keeps working unchanged against the new schema.

Reversible; the downgrade drops both columns, whose values are not
recoverable but carry no information beyond the migration moment.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-29

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in ("created_at", "updated_at"):
        op.add_column(
            "project_ai_settings",
            sa.Column(
                column,
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    op.drop_column("project_ai_settings", "updated_at")
    op.drop_column("project_ai_settings", "created_at")
