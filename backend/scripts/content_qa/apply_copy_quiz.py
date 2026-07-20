"""Apply the phase-3 generated edits (copy rewrites + quiz-quality fixes) to live lessons.

For each lesson: fetch FRESH, apply text_edits as exact single-occurrence
replacements in non-quiz prose fields, replace named quiz blocks with the
corrected questions, assert the block (id,type) skeleton is unchanged, write.
Writes a quiz changelog JSON for the human review.
"""
import asyncio
import json
import sys
import uuid
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apply_lib import connect, fetch_blocks, skeleton, write_blocks
from content_qa.blocks import NON_PROSE_KEYS

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
EDITS = json.loads((WORK / "phase3_edits.json").read_text(encoding="utf-8"))
SNAP = {les["lesson_id"]: les for les in
        json.loads((WORK / "lessons_snapshot.json").read_text(encoding="utf-8"))}


def _replace_first(node, old, new) -> bool:
    """Replace the first occurrence of `old` in any prose string under node."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in NON_PROSE_KEYS:
                continue
            if isinstance(v, str):
                if old in v:
                    node[k] = v.replace(old, new, 1)
                    return True
            elif _replace_first(v, old, new):
                return True
    elif isinstance(node, list):
        for item in node:
            if _replace_first(item, old, new):
                return True
    return False


def apply_text_edit(blocks, old, new) -> bool:
    for b in blocks:
        if b.get("type") == "quiz":
            continue
        if _replace_first(b, old, new):
            return True
    return False


def valid_question(q) -> bool:
    return (isinstance(q.get("q"), str) and isinstance(q.get("options"), list)
            and 2 <= len(q["options"]) and isinstance(q.get("correct"), int)
            and 0 <= q["correct"] < len(q["options"]) and isinstance(q.get("explanation"), str))


def apply_quiz_edit(blocks, block_id, new_questions):
    for b in blocks:
        if b.get("id") == block_id and b.get("type") == "quiz":
            for q in new_questions:
                assert valid_question(q), f"invalid question in {block_id}: {q.get('q')!r}"
            old_q = b.get("questions", [])
            for i, nq in enumerate(new_questions):
                if not nq.get("id"):
                    nq["id"] = (old_q[i]["id"] if i < len(old_q) and old_q[i].get("id")
                                else str(uuid.uuid4()))
            b["questions"] = new_questions
            return old_q
    return None


async def main() -> None:
    # group edits by lesson
    text_by_lesson = defaultdict(list)
    quiz_by_lesson = defaultdict(list)
    for mod in EDITS:
        for e in mod.get("text_edits", []):
            text_by_lesson[e["lesson_id"]].append(e)
        for qe in mod.get("quiz_edits", []):
            quiz_by_lesson[qe["lesson_id"]].append(qe)

    conn = await connect()
    text_applied = text_missed = 0
    misses = []
    quiz_changelog = []
    lessons_written = set()
    try:
        lesson_ids = set(text_by_lesson) | set(quiz_by_lesson)
        for lid in lesson_ids:
            blocks = await fetch_blocks(conn, lid)  # FRESH
            before_skel = skeleton(blocks)
            title = SNAP.get(lid, {}).get("lesson_title", lid)
            track = SNAP.get(lid, {}).get("track", "?")

            for e in text_by_lesson.get(lid, []):
                if apply_text_edit(blocks, e["old_string"], e["new_string"]):
                    text_applied += 1
                else:
                    text_missed += 1
                    misses.append({"track": track, "lesson": title,
                                   "category": e["category"], "old": e["old_string"][:80]})

            for qe in quiz_by_lesson.get(lid, []):
                old_q = apply_quiz_edit(blocks, qe["block_id"], qe["questions"])
                if old_q is None:
                    misses.append({"track": track, "lesson": title, "category": "quiz",
                                   "old": f"block {qe['block_id']} not found"})
                    continue
                quiz_changelog.append({
                    "track": track, "lesson": title, "block_id": qe["block_id"],
                    "change_summary": qe.get("change_summary", ""),
                    "old_question_count": len(old_q),
                    "new_question_count": len(qe["questions"]),
                    "old_correct_positions": [q.get("correct") for q in old_q],
                    "new_correct_positions": [q.get("correct") for q in qe["questions"]],
                })

            assert skeleton(blocks) == before_skel, f"skeleton changed for {title}!"
            await write_blocks(conn, lid, blocks)
            lessons_written.add(lid)
    finally:
        await conn.close()

    (WORK / "quiz_changelog.json").write_text(
        json.dumps(quiz_changelog, ensure_ascii=False, indent=2), encoding="utf-8")
    (WORK / "apply_misses.json").write_text(
        json.dumps(misses, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"lessons written: {len(lessons_written)}")
    print(f"text edits applied: {text_applied} | missed (no exact match): {text_missed}")
    print(f"quiz blocks corrected: {len(quiz_changelog)}")
    print(f"misses written to apply_misses.json; quiz changelog to quiz_changelog.json")


if __name__ == "__main__":
    asyncio.run(main())
