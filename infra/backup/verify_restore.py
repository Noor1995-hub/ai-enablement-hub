# /// script
# requires-python = ">=3.11"
# dependencies = ["asyncpg~=0.30"]
# ///
"""Compare a restored database against live, from a machine with no psql.

    uv run infra/backup/verify_restore.py --live "<dsn>" --restored "<dsn>" \
        [--lesson-id <uuid>]

Prints a per-table row-count comparison and, when --lesson-id is given, a deep
comparison of that lesson's content_blocks. Exits non-zero on a STRUCTURAL
problem (a table missing from the restore, or empty in the restore while live
has rows). Row-count deltas on progress/session tables are expected and are
reported, not failed — live keeps moving after the dump was taken.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid

import asyncpg

TABLES_SQL = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name
"""


async def snapshot(dsn: str) -> dict[str, int]:
    conn = await asyncpg.connect(dsn)
    try:
        names = [r["table_name"] for r in await conn.fetch(TABLES_SQL)]
        counts = {}
        for name in names:
            counts[name] = await conn.fetchval(f'SELECT count(*) FROM "{name}"')
        return counts
    finally:
        await conn.close()


async def lesson_blocks(dsn: str, lesson_id: str):
    conn = await asyncpg.connect(dsn)
    try:
        # lessons.id is a uuid column — asyncpg wants a uuid.UUID, not a str.
        return await conn.fetchval(
            "SELECT content_blocks FROM lessons WHERE id = $1", uuid.UUID(lesson_id)
        )
    finally:
        await conn.close()


def as_json(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", required=True)
    parser.add_argument("--restored", required=True)
    parser.add_argument("--lesson-id")
    args = parser.parse_args()

    live, restored = await asyncio.gather(snapshot(args.live), snapshot(args.restored))

    print(f"{'table':<32}{'restored':>10}{'live':>10}{'delta':>10}")
    failures = []
    for name in sorted(set(live) | set(restored)):
        rest_n = restored.get(name)
        live_n = live.get(name)
        shown_rest = "MISSING" if rest_n is None else rest_n
        shown_live = "MISSING" if live_n is None else live_n
        delta = "" if rest_n is None or live_n is None else f"{rest_n - live_n:+d}"
        print(f"{name:<32}{str(shown_rest):>10}{str(shown_live):>10}{delta:>10}")
        if rest_n is None and live_n is not None:
            failures.append(f"{name}: missing from the restore")
        elif rest_n == 0 and (live_n or 0) > 0:
            failures.append(f"{name}: empty in the restore but {live_n} rows live")

    if args.lesson_id:
        rest_blocks, live_blocks = await asyncio.gather(
            lesson_blocks(args.restored, args.lesson_id),
            lesson_blocks(args.live, args.lesson_id),
        )
        if rest_blocks is None:
            failures.append(f"lesson {args.lesson_id} missing from the restore")
        elif live_blocks is None:
            print(f"\nlesson {args.lesson_id} does not exist live — pick another id")
        else:
            rest_json, live_json = as_json(rest_blocks), as_json(live_blocks)
            same = rest_json == live_json
            print(
                f"\nlesson {args.lesson_id}: restored {len(rest_json)} blocks, "
                f"live {len(live_json)} blocks, identical={same}"
            )
            if not same:
                print("(a difference here is expected if the lesson was edited after the dump)")

    if failures:
        print("\nFAILED:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("\nOK: every live table is present and non-empty in the restore")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
