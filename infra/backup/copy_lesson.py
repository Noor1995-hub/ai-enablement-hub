# /// script
# requires-python = ">=3.11"
# dependencies = ["asyncpg~=0.30"]
# ///
"""Copy one lesson's content_blocks from a restored database back into live.

    $env:RESTORED_DSN = '<...dbname=ai-enablement-hub-restoredrill>'
    $env:LIVE_DSN     = '<...dbname=ai-enablement-hub>'
    uv run infra/backup/copy_lesson.py --lesson-id <uuid>           # dry run
    uv run infra/backup/copy_lesson.py --lesson-id <uuid> --apply    # WRITES to live

This is the everyday recovery step: the restore job materializes an old dump into
the scratch database, then this moves one lesson back. Dry run by default.
Postgres cannot query across databases, hence two connections.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid

import asyncpg

SELECT = "SELECT title, content_blocks FROM lessons WHERE id = $1"
UPDATE = "UPDATE lessons SET content_blocks = $2 WHERE id = $1"


def as_json(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lesson-id", required=True)
    parser.add_argument("--apply", action="store_true", help="actually write to LIVE_DSN")
    args = parser.parse_args()

    for var in ("RESTORED_DSN", "LIVE_DSN"):
        if not os.environ.get(var, "").strip():
            print(f"FATAL: set {var} first", file=sys.stderr)
            return 2

    lesson_id = uuid.UUID(args.lesson_id)
    src = await asyncpg.connect(os.environ["RESTORED_DSN"])
    dst = await asyncpg.connect(os.environ["LIVE_DSN"])
    try:
        old = await src.fetchrow(SELECT, lesson_id)
        current = await dst.fetchrow(SELECT, lesson_id)
        if old is None:
            print(f"FATAL: lesson {lesson_id} not in the restored database", file=sys.stderr)
            return 3
        if current is None:
            print(f"FATAL: lesson {lesson_id} not in the live database", file=sys.stderr)
            return 3

        restored_blocks = as_json(old["content_blocks"])
        live_blocks = as_json(current["content_blocks"])
        print(f"lesson: {old['title']}")
        print(f"  restored: {len(restored_blocks)} blocks")
        print(f"  live:     {len(live_blocks)} blocks")
        print(f"  identical: {restored_blocks == live_blocks}")

        if not args.apply:
            print("\ndry run — nothing written. Re-run with --apply to overwrite live.")
            return 0

        await dst.execute(UPDATE, lesson_id, old["content_blocks"])
        print("\napplied: live content_blocks replaced with the restored version")
    finally:
        await src.close()
        await dst.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
