"""one interview conversation per user — partial unique index

Review finding 6.5. InterviewService treats "one `interview` conversation per
user" as an invariant (`_interview_conversation` returns `conversations[0]`,
`open_interview` is check-then-create), but nothing enforced it: two
concurrent openers could create two rows and leave one transcript
permanently invisible. The code now inserts through
`ConversationRepository.create_interview_if_absent` (ON CONFLICT DO NOTHING on
this index), so a lost race returns the winner's conversation, not a 500.

A PARTIAL unique index, not a unique constraint: chat kinds are many-per-user
by design, so only `kind = 'interview'` is constrained. Not deferrable (unlike
d4e5f6a7b8c9): nothing ever needs two interview rows mid-transaction, and
ON CONFLICT cannot use a deferrable arbiter.

Verified against prod (progress.md, read-only, 2026-09-29): 0 users have more
than one interview conversation, so the index builds cleanly. This migration
deliberately does NOT de-duplicate: an interview conversation is a learner's
transcript, and choosing which one to destroy is a human decision, not a
migration's.

Live data: additive, writes no rows; `conversations` is small, so the build
is well inside the migrate job's budget. Expand-first: an older image keeps
working against the new schema: the Interview page always loads the existing
conversation id before posting a turn, so the old image only tries a second
interview row in a race or on a hand-crafted id-less POST, and that one
request now fails (500) instead of silently hiding a transcript.

Reversible without loss (downgrade drops the index).

Revision ID: c3d4e5f6a7b8
Revises: d4e5f6a7b8c9
Create Date: 2026-09-30

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_NAME = "uq_conversations_interview_user_id"


def upgrade() -> None:
    op.create_index(
        _INDEX_NAME,
        "conversations",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'interview'"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="conversations")
