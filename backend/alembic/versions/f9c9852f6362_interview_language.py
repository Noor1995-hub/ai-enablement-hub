"""interview language on the conversation

#83: the learner picks the interview language (English or Dutch) on the
interview's welcome screen; it is stored on their interview conversation and
drives the opener, every chat turn and the playbook.

Live data: additive, one nullable column with no default, so no row is
rewritten and `conversations` stays small: well inside the migrate job's
budget. NULL means English (every interview before the picker, and every
non-interview kind). Expand-first: an older image never reads or writes the
column and keeps working against the new schema.

Reversible without loss of anything but the language choices themselves
(downgrade drops the column).

Revision ID: f9c9852f6362
Revises: e5f6a7b8c9d0
Create Date: 2026-10-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f9c9852f6362"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("language", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "language")
