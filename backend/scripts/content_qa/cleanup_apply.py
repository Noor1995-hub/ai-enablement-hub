"""Apply the residual-quiz punctuation cleanup with strict structure validation.

For each corrected quiz block: match by block_id to its lesson (from
cleanup_blocks.json), fetch fresh, verify the correction preserved the question
count, per-question option counts, and every "correct" index (these were
keep-verdict quizzes - only wording should change), verify no banned
punctuation remains, then replace the questions and write.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apply_lib import connect, fetch_blocks, skeleton, write_blocks
from content_qa.checks import find_banned_punctuation

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
CORRECTED = json.loads((WORK / "cleanup_result.json").read_text(encoding="utf-8"))["blocks"]
COLLECTED = json.loads((WORK / "cleanup_blocks.json").read_text(encoding="utf-8"))

# block_id -> (lesson_id, original block)
BLOCK_INFO = {c["block"]["id"]: (c["lesson_id"], c["lesson_title"], c["block"]) for c in COLLECTED}


async def main() -> None:
    conn = await connect()
    written = 0
    skipped = []
    try:
        # group corrected blocks by lesson so one write covers a lesson
        by_lesson = {}
        for cb in CORRECTED:
            bid = cb["block_id"]
            if bid not in BLOCK_INFO:
                skipped.append((bid, "unknown block_id"))
                continue
            lesson_id, title, orig = BLOCK_INFO[bid]
            # structural checks vs the collected original
            orig_q = orig["questions"]
            new_q = cb["questions"]
            if len(new_q) != len(orig_q):
                skipped.append((title, f"question count {len(orig_q)}->{len(new_q)}"))
                continue
            if [q.get("correct") for q in new_q] != [q.get("correct") for q in orig_q]:
                skipped.append((title, "correct indices changed"))
                continue
            if [len(q["options"]) for q in new_q] != [len(q["options"]) for q in orig_q]:
                skipped.append((title, "option counts changed"))
                continue
            # no banned punctuation in the corrected block
            if find_banned_punctuation([{"id": bid, "type": "quiz", "questions": new_q}]):
                skipped.append((title, "still has banned punctuation"))
                continue
            by_lesson.setdefault(lesson_id, {})[bid] = new_q

        for lesson_id, blockmap in by_lesson.items():
            blocks = await fetch_blocks(conn, lesson_id)  # FRESH
            before = skeleton(blocks)
            changed = False
            for b in blocks:
                if b.get("id") in blockmap and b.get("type") == "quiz":
                    b["questions"] = blockmap[b["id"]]
                    changed = True
            if changed:
                assert skeleton(blocks) == before
                await write_blocks(conn, lesson_id, blocks)
                written += 1
    finally:
        await conn.close()
    print(f"cleaned quiz blocks written across {written} lessons")
    if skipped:
        print(f"skipped {len(skipped)}:")
        for s in skipped:
            print(f"   {s}")


if __name__ == "__main__":
    asyncio.run(main())
