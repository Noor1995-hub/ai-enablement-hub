"""Recover phase-3 edits whose lesson_id/block_id the agent fabricated.

For any edit whose lesson_id is not a real in-scope lesson, find the real
lesson whose FRESH content contains the edit's old_string and apply it there.
Orphaned quiz edits (invalid block_id) are matched to a quiz block by locating
which lesson currently holds a quiz, using the edit's change_summary for the
human to confirm.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apply_lib import connect, fetch_blocks, skeleton, write_blocks
from apply_copy_quiz import apply_quiz_edit, apply_text_edit

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
EDITS = json.loads((WORK / "phase3_edits.json").read_text(encoding="utf-8"))
SNAP = json.loads((WORK / "lessons_snapshot.json").read_text(encoding="utf-8"))
REAL_IDS = {les["lesson_id"] for les in SNAP}
TITLE = {les["lesson_id"]: (les["track"], les["lesson_title"]) for les in SNAP}


def contains(blocks, needle) -> bool:
    return needle in json.dumps(blocks, ensure_ascii=False)


async def main() -> None:
    # collect mis-attributed edits
    bad_text = []
    bad_quiz = []
    for mod in EDITS:
        for e in mod.get("text_edits", []):
            if e["lesson_id"] not in REAL_IDS:
                bad_text.append(e)
        for qe in mod.get("quiz_edits", []):
            if qe["lesson_id"] not in REAL_IDS:
                bad_quiz.append(qe)
    print(f"mis-attributed: {len(bad_text)} text, {len(bad_quiz)} quiz")

    conn = await connect()
    fresh = {}
    try:
        for les in SNAP:
            fresh[les["lesson_id"]] = await fetch_blocks(conn, les["lesson_id"])

        applied = 0
        still_missed = []
        touched = {}
        for e in bad_text:
            target = None
            for lid, blocks in fresh.items():
                # search non-quiz text for the old_string
                if any(
                    e["old_string"] in json.dumps(b, ensure_ascii=False)
                    for b in blocks
                    if b.get("type") != "quiz"
                ):
                    target = lid
                    break
            if target and apply_text_edit(fresh[target], e["old_string"], e["new_string"]):
                applied += 1
                touched.setdefault(target, 0)
                touched[target] += 1
            else:
                still_missed.append(e["old_string"][:70])

        # write back the lessons we touched (skeleton preserved by text edits)
        for lid, n in touched.items():
            await write_blocks(conn, lid, fresh[lid])
            print(f"  recovered {n} edits -> [{TITLE[lid][0]}] {TITLE[lid][1]}")

        print(f"text recovered: {applied} | still missed: {len(still_missed)}")
        for s in still_missed:
            print(f"    STILL MISSED: {s}")

        # orphan quiz edits: report for mapping
        for qe in bad_quiz:
            print(f"\nORPHAN QUIZ EDIT (block {qe['block_id']}):")
            print(f"  change_summary: {qe.get('change_summary', '')[:300]}")
            print(f"  new question count: {len(qe['questions'])}")
            print(f"  first q: {qe['questions'][0]['q'][:90]}")
    finally:
        await conn.close()


asyncio.run(main())
