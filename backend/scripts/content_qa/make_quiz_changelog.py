"""Format the applied quiz changes into a human-checkable markdown report,
and list the lessons where the American 'Artifact(s)' product name was kept.
"""
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apply_lib import connect, fetch_blocks
from content_qa.checks import find_americanisms

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
OUT = Path(__file__).resolve().parents[2].parent / "scratch_review"
CL = json.loads((WORK / "quiz_changelog.json").read_text(encoding="utf-8"))
SNAP = json.loads((WORK / "lessons_snapshot.json").read_text(encoding="utf-8"))


async def artifact_lessons():
    conn = await connect()
    out = []
    try:
        for les in SNAP:
            blocks = await fetch_blocks(conn, les["lesson_id"])
            hits = [a for a in find_americanisms(blocks) if a["term"].lower() in ("artifact", "artifacts")]
            if hits:
                out.append((les["track"], les["lesson_title"], len(hits)))
    finally:
        await conn.close()
    return out


def main() -> None:
    by_track = defaultdict(list)
    for e in CL:
        by_track[e["track"]].append(e)

    lines = [
        "# Quiz changes applied to live content (2026-07-20)", "",
        "Every quiz change made during the apply phase, for your review. Corrections only "
        "(position-shuffles, trimming untaught/duplicate questions, distractor fixes, and "
        "punctuation/spelling inside quizzes). Quiz-to-interactive conversions and the one quiz "
        "drop were NOT applied - they are listed separately for your sign-off.", "",
        f"**{len(CL)} quizzes changed.** Full backup of pre-change content: "
        "`admin_content_qa_2026-07-20/live_backup_20260720_apply.json`.", "",
    ]
    for track in sorted(by_track):
        lines.append(f"\n## {track}")
        for e in by_track[track]:
            trimmed = e["new_question_count"] != e["old_question_count"]
            cnt = (f"now {e['new_question_count']} questions"
                   + (f" (was {e['old_question_count']})" if trimmed else ""))
            lines.append(f"\n### {e['lesson']}")
            lines.append(f"- **{cnt}**; correct-answer positions now "
                         f"{e['new_correct_positions']}")
            lines.append(f"- {e['change_summary']}")
    (OUT / "quiz_changes_applied_2026-07-20.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote quiz_changes_applied_2026-07-20.md")


if __name__ == "__main__":
    main()
    print("\n=== lessons where American 'Artifact(s)' product name was KEPT ===")
    for track, title, n in asyncio.run(artifact_lessons()):
        print(f"  [{track}] {title}: {n}")
