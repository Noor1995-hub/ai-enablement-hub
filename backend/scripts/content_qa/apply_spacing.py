"""Apply the house quiz-spacing convention to live lessons.

For every quiz missing a 'Check your understanding' heading and/or a
whitespace(md) separator in the 3 blocks before it, insert the missing
block(s) so the close reads: ... whitespace(md) > heading 'Check your
understanding' > quiz. Fetches fresh, inserts, then RE-RUNS the conformance
checker and asserts no spacing gap remains before writing.
"""
import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts/ on path (no PYTHONPATH needed)

from apply_lib import connect, fetch_blocks, write_blocks
from content_qa.checks import CHECK_UNDERSTANDING, WINDOW, check_quiz_conformance

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
SNAP = json.loads((WORK / "lessons_snapshot.json").read_text(encoding="utf-8"))


def new_heading() -> dict:
    return {"id": str(uuid.uuid4()), "type": "heading", "level": 2,
            "text": "Check your understanding"}


def new_ws() -> dict:
    return {"id": str(uuid.uuid4()), "type": "whitespace", "size": "md"}


def _is_cyu(b: dict) -> bool:
    return (b.get("type") == "heading"
            and (b.get("text") or "").strip().lower() == CHECK_UNDERSTANDING)


def _is_md_ws(b: dict) -> bool:
    return b.get("type") == "whitespace" and b.get("size") == "md"


def _needs_fix(blocks: list[dict], qi: int) -> bool:
    window = blocks[max(0, qi - WINDOW):qi]
    return not (any(_is_cyu(w) for w in window) and any(_is_md_ws(w) for w in window))


def fix_blocks(blocks: list[dict]) -> tuple[list[dict], int]:
    """Canonicalise the close of every non-conforming quiz to
    ... whitespace(md) > heading 'Check your understanding' > quiz.

    Builds a new list; when a quiz needs fixing, strips any stray CYU heading or
    md-whitespace from the last few emitted blocks (so the heading isn't
    duplicated and the separator isn't stranded), then appends a fresh
    whitespace(md) + heading pair immediately before the quiz.
    """
    out: list[dict] = []
    fixed = 0
    for i, b in enumerate(blocks):
        if b.get("type") == "quiz" and _needs_fix(blocks, i):
            cut = max(0, len(out) - 4)
            out = out[:cut] + [x for x in out[cut:] if not (_is_cyu(x) or _is_md_ws(x))]
            out.append(new_ws())
            out.append(new_heading())
            fixed += 1
        out.append(b)
    return out, fixed


async def main() -> None:
    conn = await connect()
    lessons_changed = 0
    quizzes_fixed = 0
    try:
        for les in SNAP:
            lid = les["lesson_id"]
            blocks = await fetch_blocks(conn, lid)  # FRESH
            new_blocks, nfix = fix_blocks(blocks)
            if nfix == 0:
                continue
            # assert no spacing gap remains
            remaining = [f for f in check_quiz_conformance(new_blocks)
                         if f["kind"] in ("quiz-no-cyu-heading", "quiz-no-md-separator")]
            assert not remaining, f"{les['lesson_title']}: still has {remaining}"
            await write_blocks(conn, lid, new_blocks)
            lessons_changed += 1
            quizzes_fixed += nfix
            print(f"[{les['track']}] {les['lesson_title']}: fixed spacing on {nfix} quiz(zes)")
    finally:
        await conn.close()
    print(f"\nDONE: spacing fixed on {quizzes_fixed} quizzes across {lessons_changed} lessons.")


asyncio.run(main())
