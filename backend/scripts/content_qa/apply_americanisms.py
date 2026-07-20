"""Apply deterministic British-English fixes to live lessons.

Case-preserving whole-word replacement using the AMERICANISMS map, EXCLUDING
'artifact'/'artifacts' (Anthropic product name - held for human judgement).
Fetches each lesson fresh, transforms only string values, asserts the block
skeleton is unchanged, then writes. Prints a per-change log.
"""
import asyncio
import re

from apply_lib import connect, fetch_blocks, skeleton, transform_texts, write_blocks
from content_qa.checks import AMERICANISMS

EXCLUDE = {"artifact", "artifacts"}
FIXES = {k: v for k, v in AMERICANISMS.items() if k not in EXCLUDE}
_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in FIXES) + r")\b", re.IGNORECASE)

# lesson_ids come from the snapshot (in-scope set)
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
SNAP = json.loads((WORK / "lessons_snapshot.json").read_text(encoding="utf-8"))


def match_case(src: str, repl: str) -> str:
    if src.isupper():
        return repl.upper()
    if src[0].isupper():
        return repl[0].upper() + repl[1:]
    return repl


def make_fixer(log: list):
    def fix(text: str) -> str:
        def sub(m: re.Match) -> str:
            src = m.group(1)
            repl = match_case(src, FIXES[src.lower()])
            log.append((src, repl))
            return repl
        return _RE.sub(sub, text)
    return fix


async def main() -> None:
    conn = await connect()
    total_changes = 0
    changed_lessons = 0
    try:
        for les in SNAP:
            lid = les["lesson_id"]
            blocks = await fetch_blocks(conn, lid)  # FRESH
            before_skel = skeleton(blocks)
            log: list = []
            new_blocks = transform_texts(blocks, make_fixer(log))
            if not log:
                continue
            assert skeleton(new_blocks) == before_skel, f"skeleton changed for {lid}!"
            await write_blocks(conn, lid, new_blocks)
            changed_lessons += 1
            total_changes += len(log)
            pairs = ", ".join(f"{s}->{r}" for s, r in log)
            print(f"[{les['track']}] {les['lesson_title']}: {len(log)} ({pairs})")
    finally:
        await conn.close()
    print(f"\nDONE: {total_changes} replacements across {changed_lessons} lessons "
          f"(artifact/artifacts excluded).")


asyncio.run(main())
