"""Fix the Claude 'Scheduled tasks and plugins' lesson.

Facts (confirmed by Matthias, 2026-07-20):
- Scheduled tasks run on YOUR machine and only fire while the computer is awake
  and online; a "Keep awake" setting solves the away-from-desk case.
- A scheduled task CAN work in a folder/project on your computer (edit local
  files), same as a task you run yourself. The old "cannot be tied to a folder"
  limit was wrong.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apply_lib import connect, fetch_blocks, skeleton, write_blocks
from content_qa.checks import find_banned_punctuation

LESSON = None  # resolved by title
TITLE = "Scheduled tasks and plugins"
CARD_ID = "d2059321-8387-4aac-825b-c4f9cf16d156"
QUIZ_BLOCK_ID = "4b59ab54-b8d5-4d97-ad0b-f719775c6039"
QUESTION_ID = "c691b41b-3e78-4a7b-b3c6-48cf897dcc5a"

BODY2 = (
    "A scheduled task lets you describe a recurring job once and then have Cowork run it on its "
    "own cadence. You do not start it each time, it just happens on schedule, whether or not you "
    "are actively at your desk.\n\n"
    "One thing to know: a scheduled task runs on your own machine, so your computer needs to be "
    "awake and online when the task is due. To let a task fire while you are away from the "
    'keyboard, turn on the "Keep awake" setting on the Scheduled screen, which stops the machine '
    "going to sleep so the task can still run."
)
BODY6 = (
    "A scheduled task has the same abilities as any task you run yourself. Your connectors, your "
    "skills and your installed plugins are all available, and it can work inside a folder or "
    "project on your computer, editing the files there, exactly as a task you start by hand can. "
    "So a scheduled job can take almost any shape: pulling from your connected tools and producing "
    "a report, running web research on a cadence, or maintaining the files in a project folder for "
    "you."
)
CARD_BODY = (
    "Make work recurring. Describe a job once and Claude runs it on a set cadence while your "
    "computer is awake and online. Great for routine jobs across your connected tools, skills and "
    "project folders."
)
NEW_Q = {
    "id": QUESTION_ID,
    "q": "A scheduled task is due to run, but your computer is asleep and the Keep awake setting "
    "is off. What happens?",
    "options": [
        "It runs anyway, because scheduled tasks execute in the cloud",
        "It does not run until your computer is awake and online again. Turning on Keep awake "
        "would let it fire on time",
        "It runs, but only the steps that do not need the internet",
        "Cowork sends you the result without running the task",
    ],
    "correct": 1,
    "explanation": "Scheduled tasks run on your own machine, so they need it awake and online at "
    "the scheduled time. The Keep awake setting stops the computer sleeping so a "
    "task can fire while you are away.",
}


async def main() -> None:
    import json

    snap = json.loads(
        (
            Path(__file__).resolve().parents[2].parent
            / "scratch_review"
            / "admin_content_qa_2026-07-20"
            / "lessons_snapshot.json"
        ).read_text(encoding="utf-8")
    )
    lesson_id = next(l["lesson_id"] for l in snap if l["lesson_title"] == TITLE)

    conn = await connect()
    try:
        blocks = await fetch_blocks(conn, lesson_id)
        before = skeleton(blocks)
        changes = []
        for b in blocks:
            if b.get("type") == "paragraph" and "whether or not you are at your machine" in (
                b.get("text") or ""
            ):
                b["text"] = BODY2
                changes.append("body-2 (awake + Keep awake)")
            elif b.get("type") == "paragraph" and "cannot be tied to a folder" in (
                b.get("text") or ""
            ):
                b["text"] = BODY6
                changes.append("body-6 (folder/project ability)")
            elif b.get("type") == "card_group":
                for c in b.get("cards", []):
                    if c.get("id") == CARD_ID:
                        c["body"] = CARD_BODY
                        changes.append("card (Scheduled tasks)")
            elif b.get("type") == "quiz" and b.get("id") == QUIZ_BLOCK_ID:
                for i, q in enumerate(b["questions"]):
                    if q.get("id") == QUESTION_ID:
                        b["questions"][i] = NEW_Q
                        changes.append("quiz Q (asleep)")
        assert skeleton(blocks) == before, "skeleton changed!"
        assert not find_banned_punctuation(blocks), "introduced banned punctuation!"
        await write_blocks(conn, lesson_id, blocks)
    finally:
        await conn.close()
    print("applied:", ", ".join(changes) if changes else "NOTHING MATCHED")


if __name__ == "__main__":
    asyncio.run(main())
