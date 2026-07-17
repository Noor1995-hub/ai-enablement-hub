"""introduction track

Adds tracks.is_introduction and inserts the single mandatory pre-Explorer
"Introduction" track (empty — content authored later via the admin UI). No CHECK
constraints change: the track keeps required_level='explore' (always unlocked)
and is distinguished only by is_introduction=true.

Revision ID: f3a4b5c6d7e8
Revises: d8e9f0a1b2c3
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "d8e9f0a1b2c3"
branch_labels: str | None = None
depends_on: str | None = None

# Exposed for the migration-sanity test (runs it against the test schema).
# Ships the Introduction track with a placeholder module + lesson so the group is
# immediately visible (with editable content) rather than an empty shell — the
# admin replaces "Placeholder" with real orientation content. Note this makes the
# completion gate LIVE on deploy: other tracks lock until the learner clears this
# lesson (trivial — no quiz), then the admin's real content makes it meaningful.
INTRODUCTION_SQL = """
WITH intro_track AS (
    INSERT INTO tracks (name, sort_order, track_type, color, required_level, is_introduction)
    VALUES ('Introduction', 0, 'general', '#941914', 'explore', true)
    RETURNING id
), intro_module AS (
    INSERT INTO modules (track_id, title, sort_order)
    SELECT id, 'Introduction', 0 FROM intro_track
    RETURNING id
)
INSERT INTO lessons (module_id, title, sort_order)
SELECT id, 'Placeholder', 0 FROM intro_module
"""


def upgrade() -> None:
    op.add_column(
        "tracks",
        sa.Column(
            "is_introduction",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(INTRODUCTION_SQL)


def downgrade() -> None:
    op.execute("DELETE FROM tracks WHERE is_introduction = true")
    op.drop_column("tracks", "is_introduction")
