"""Re-fetch all 91 in-scope lessons FRESH and re-run the deterministic checks.

Read-only. Prints remaining counts per category so we can confirm the apply
passes landed (em-dashes -> 0, spacing gaps -> 0, americanisms -> only the
held artifact/artifacts, etc.).
"""
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apply_lib import connect, fetch_blocks
from content_qa.checks import check_quiz_conformance, find_americanisms, find_banned_punctuation

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
SNAP = json.loads((WORK / "lessons_snapshot.json").read_text(encoding="utf-8"))


async def main() -> None:
    conn = await connect()
    punct = 0
    amer: Counter = Counter()
    conf: Counter = Counter()
    punct_lessons = []
    try:
        for les in SNAP:
            blocks = await fetch_blocks(conn, les["lesson_id"])
            p = find_banned_punctuation(blocks)
            if p:
                punct += len(p)
                punct_lessons.append((les["track"], les["lesson_title"], len(p)))
            for a in find_americanisms(blocks):
                amer[a["term"].lower()] += 1
            for c in check_quiz_conformance(blocks):
                conf[c["kind"]] += 1
    finally:
        await conn.close()
    print(f"banned-punctuation remaining: {punct}")
    for t, title, n in punct_lessons:
        print(f"    [{t}] {title}: {n}")
    print(f"americanisms remaining: {sum(amer.values())} -> {dict(amer)}")
    print(f"quiz-conformance remaining: {dict(conf)}")


asyncio.run(main())
