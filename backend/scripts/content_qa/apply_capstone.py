"""Apply the For Developers Capstone cross-reference rewrite (exact-match edits)."""
import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from apply_lib import connect, fetch_blocks, skeleton, write_blocks
from apply_copy_quiz import apply_text_edit

CAPSTONE_LESSON = "cb9ed358-68e5-442d-8838-6963beab3228"
SRC = pathlib.Path(
    r"C:\Users\danneelm\AppData\Local\Temp\claude\c--Users-danneelm-projects-AI-enablement-hub-AI-ENABLEMENT-HUB-REBUILD\cd3739d2-3f71-4307-b426-567bbe83cd15\tasks\wfwegmhyz.output"
)
EDITS = json.loads(SRC.read_text(encoding="utf-8"))["result"]["text_edits"]


async def main() -> None:
    conn = await connect()
    applied = missed = 0
    misses = []
    try:
        blocks = await fetch_blocks(conn, CAPSTONE_LESSON)
        before = skeleton(blocks)
        for e in EDITS:
            if apply_text_edit(blocks, e["old_string"], e["new_string"]):
                applied += 1
            else:
                missed += 1
                misses.append(e["old_string"][:70])
        assert skeleton(blocks) == before, "skeleton changed!"
        await write_blocks(conn, CAPSTONE_LESSON, blocks)
    finally:
        await conn.close()
    print(f"capstone edits applied: {applied} | missed: {missed}")
    for m in misses:
        print(f"    MISS: {m}")


if __name__ == "__main__":
    asyncio.run(main())
