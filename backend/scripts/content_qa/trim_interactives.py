"""Trim the authored interactive blocks to a max of 4 items / candidates.

sort: keep one item per bucket (bucket coverage), then fill in authored order up
to 4. spot_the_flaw: keep at least one flaw and one non-flaw, up to 4 total.
Locates each block in the live lesson by its (unique) prompt, trims in place.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apply_lib import connect, fetch_blocks, write_blocks

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
CONV = json.loads((WORK / "convert_result.json").read_text(encoding="utf-8"))
SNAP = {l["lesson_title"]: l["lesson_id"] for l in
        json.loads((WORK / "lessons_snapshot.json").read_text(encoding="utf-8"))}
MAX = 4


def trim_sort(items: list[dict]) -> list[dict]:
    by_bucket: dict = {}
    for it in items:
        by_bucket.setdefault(it["bucketId"], []).append(it)
    kept, seen = [], set()
    for bid, group in by_bucket.items():  # one per bucket first (authored order)
        kept.append(group[0]); seen.add(id(group[0]))
    for it in items:  # fill in authored order
        if len(kept) >= MAX:
            break
        if id(it) not in seen:
            kept.append(it); seen.add(id(it))
    # preserve authored order among kept
    return [it for it in items if id(it) in seen][:MAX]


def trim_flaw(cands: list[dict]) -> list[dict]:
    flaws = [c for c in cands if c.get("isFlaw")]
    nonflaws = [c for c in cands if not c.get("isFlaw")]
    kept = []
    # guarantee >=1 flaw and >=1 non-flaw, then balance toward 4
    if flaws:
        kept.append(flaws[0])
    if nonflaws:
        kept.append(nonflaws[0])
    for c in cands:
        if len(kept) >= MAX:
            break
        if c not in kept:
            kept.append(c)
    return [c for c in cands if c in kept][:MAX]


async def main() -> None:
    conn = await connect()
    report = []
    try:
        for c in CONV:
            lid = SNAP[c["lesson_title"]]
            prompt = c["new_block"]["prompt"]
            blocks = await fetch_blocks(conn, lid)
            blk = next((b for b in blocks
                        if b.get("type") == "interactive" and b.get("prompt") == prompt), None)
            if blk is None:
                report.append((c["lesson_title"], "NOT FOUND", 0, 0)); continue
            if blk["mode"] == "sort":
                before = len(blk["items"])
                if before > MAX:
                    blk["items"] = trim_sort(blk["items"])
                after = len(blk["items"])
            else:
                before = len(blk["candidates"])
                if before > MAX:
                    blk["candidates"] = trim_flaw(blk["candidates"])
                after = len(blk["candidates"])
            if after != before:
                await write_blocks(conn, lid, blocks)
            report.append((c["lesson_title"], blk["mode"], before, after))
    finally:
        await conn.close()
    for title, mode, b, a in report:
        flag = "" if a <= MAX else "  <<STILL OVER"
        print(f"  [{mode}] {b}->{a}{flag}  {title[:45]}")


if __name__ == "__main__":
    asyncio.run(main())
