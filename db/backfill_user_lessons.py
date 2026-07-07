# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Re-run the user_lessons backfill for lessons synced in after the original migration.

Migration a3f8c1d2e4b7 (2026-07-06) backfilled user_lessons once, from whatever
was in `lessons` at the time (only the General track's 24 lessons existed on
Azure then). sync_content_from_supabase.py has since added the remaining
tool-track lessons, which never got backfilled — so every user already
assigned (via user_modules) to a tool-track module currently sees "no lessons"
for it, even though the lessons exist.

This re-runs the exact same idempotent query the migration used: it only adds
user_lessons rows for (user, lesson) pairs where that user already has a
user_modules row for the lesson's module. It never deletes, and never grants
access to a module a user isn't already assigned to.

Usage:
    uv run backfill_user_lessons.py               # dry run, prints the plan
    uv run backfill_user_lessons.py --apply        # writes to Azure
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg

ENV_FILE = Path(__file__).parent / ".env"


def owner_dsn() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("AZURE_PG_OWNER_DSN="):
            return line.partition("=")[2].strip()
    sys.exit("AZURE_PG_OWNER_DSN not found in db/.env")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write changes to Azure (default: dry run)")
    args = parser.parse_args()

    with psycopg.connect(owner_dsn()) as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT um.user_id, l.id
            FROM user_modules um
            JOIN lessons l ON l.module_id = um.module_id
            LEFT JOIN user_lessons ul ON ul.user_id = um.user_id AND ul.lesson_id = l.id
            WHERE ul.id IS NULL
            """
        )
        missing = cur.fetchall()
        print(f"{len(missing)} (user, lesson) pairs missing a user_lessons row.")

        if args.apply:
            cur.execute(
                """
                INSERT INTO user_lessons (user_id, lesson_id)
                SELECT um.user_id, l.id
                FROM user_modules um
                JOIN lessons l ON l.module_id = um.module_id
                ON CONFLICT (user_id, lesson_id) DO NOTHING
                """
            )
            print(f"Inserted {cur.rowcount} rows.")
            conn.commit()
            print("Applied and committed.")
        else:
            conn.rollback()
            print("DRY RUN — no changes written. Re-run with --apply to write to Azure.")


if __name__ == "__main__":
    main()
