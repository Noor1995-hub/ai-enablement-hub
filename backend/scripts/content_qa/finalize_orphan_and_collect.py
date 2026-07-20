"""Apply the orphaned quiz edit to the real Skills lesson, and collect the
residual banned-punctuation blocks for a targeted cleanup pass.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apply_lib import connect, fetch_blocks, skeleton, write_blocks
from apply_copy_quiz import apply_quiz_edit
from content_qa.checks import find_banned_punctuation

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
EDITS = json.loads((WORK / "phase3_edits.json").read_text(encoding="utf-8"))
SNAP = json.loads((WORK / "lessons_snapshot.json").read_text(encoding="utf-8"))
REAL_IDS = {les["lesson_id"] for les in SNAP}
TITLE = {les["lesson_id"]: (les["track"], les["lesson_title"]) for les in SNAP}
SKILLS_LESSON = "9180fbce-85f7-4d9b-a73b-6187563eb656"  # Skills and subagents for engineering work


async def main() -> None:
    orphan_qe = None
    for mod in EDITS:
        for qe in mod.get("quiz_edits", []):
            if qe["lesson_id"] not in REAL_IDS:
                orphan_qe = qe
    conn = await connect()
    changelog_add = []
    try:
        # --- apply orphan quiz to the real Skills lesson ---
        if orphan_qe:
            blocks = await fetch_blocks(conn, SKILLS_LESSON)
            before = skeleton(blocks)
            quiz_ids = [b["id"] for b in blocks if b.get("type") == "quiz"]
            if len(quiz_ids) == 1:
                old_q = apply_quiz_edit(blocks, quiz_ids[0], orphan_qe["questions"])
                assert skeleton(blocks) == before
                await write_blocks(conn, SKILLS_LESSON, blocks)
                changelog_add.append({
                    "track": "Claude II", "lesson": "Skills and subagents for engineering work",
                    "block_id": quiz_ids[0], "change_summary": orphan_qe.get("change_summary", ""),
                    "old_question_count": len(old_q), "new_question_count": len(orphan_qe["questions"]),
                    "old_correct_positions": [q.get("correct") for q in old_q],
                    "new_correct_positions": [q.get("correct") for q in orphan_qe["questions"]],
                })
                print(f"orphan quiz applied to Skills lesson (quiz {quiz_ids[0]}): "
                      f"{len(old_q)} -> {len(orphan_qe['questions'])} questions")
            else:
                print(f"WARNING: Skills lesson has {len(quiz_ids)} quiz blocks, not applying orphan")

        # --- collect residual banned-punctuation blocks ---
        residual = []
        for les in SNAP:
            blocks = await fetch_blocks(conn, les["lesson_id"])
            hits = find_banned_punctuation(blocks)
            if not hits:
                continue
            hit_block_idx = {int(h["path"].split("]")[0].split("[")[1]) for h in hits}
            for idx in sorted(hit_block_idx):
                residual.append({
                    "lesson_id": les["lesson_id"], "track": les["track"],
                    "lesson_title": les["lesson_title"], "block": blocks[idx],
                })
    finally:
        await conn.close()

    (WORK / "cleanup_blocks.json").write_text(
        json.dumps(residual, ensure_ascii=False, indent=2), encoding="utf-8")
    # merge changelog addition
    cl_path = WORK / "quiz_changelog.json"
    cl = json.loads(cl_path.read_text(encoding="utf-8")) if cl_path.exists() else []
    cl.extend(changelog_add)
    cl_path.write_text(json.dumps(cl, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"residual blocks with banned punctuation: {len(residual)} "
          f"(across {len({r['lesson_id'] for r in residual})} lessons)")


if __name__ == "__main__":
    asyncio.run(main())
