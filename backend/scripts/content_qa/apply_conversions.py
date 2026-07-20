"""Apply quiz->interactive conversions and the one quiz drop to live lessons.

Conversions: fetch fresh, find the quiz block by id, validate the authored
interactive block, regenerate all ids to fresh uuids (remapping bucket refs),
swap it in at the same index. Drop: remove the quiz plus its orphaned
'Check your understanding' heading + md whitespace lead-in.
"""
import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apply_lib import connect, fetch_blocks, write_blocks
from content_qa.checks import CHECK_UNDERSTANDING

WORK = Path(__file__).resolve().parents[2].parent / "scratch_review" / "admin_content_qa_2026-07-20"
CONV = json.loads((WORK / "convert_result.json").read_text(encoding="utf-8"))
SNAP = json.loads((WORK / "lessons_snapshot.json").read_text(encoding="utf-8"))
TITLE_TO_ID = {les["lesson_title"]: les["lesson_id"] for les in SNAP}

DROP = [("When to use Chat and when Cowork", "Claude")]  # lesson_title, track


def validate_and_normalise(nb: dict) -> dict:
    """Validate an authored interactive block; return a copy with fresh uuids."""
    assert nb.get("type") == "interactive", "not interactive"
    mode = nb.get("mode")
    assert mode in ("sort", "spot_the_flaw"), f"bad mode {mode}"
    out = {"id": str(uuid.uuid4()), "type": "interactive", "mode": mode,
           "prompt": nb["prompt"]}
    if mode == "sort":
        assert len(nb.get("buckets", [])) >= 2 and nb.get("items"), "sort needs buckets+items"
        idmap = {}
        buckets = []
        for b in nb["buckets"]:
            nid = str(uuid.uuid4()); idmap[b["id"]] = nid
            buckets.append({"id": nid, "label": b["label"]})
        items = []
        for it in nb["items"]:
            assert it["bucketId"] in idmap, f"item bucketId {it['bucketId']} has no bucket"
            items.append({"id": str(uuid.uuid4()), "text": it["text"],
                          "bucketId": idmap[it["bucketId"]], "reason": it["reason"]})
        out["buckets"] = buckets
        out["items"] = items
    else:  # spot_the_flaw
        cands = nb.get("candidates", [])
        assert len(cands) >= 2, "spot_the_flaw needs candidates"
        assert any(c["isFlaw"] for c in cands) and any(not c["isFlaw"] for c in cands), \
            "need at least one flaw and one non-flaw"
        assert nb.get("example"), "spot_the_flaw needs example"
        out["example"] = nb["example"]
        out["candidates"] = [{"id": str(uuid.uuid4()), "text": c["text"],
                              "isFlaw": bool(c["isFlaw"]), "reason": c["reason"]} for c in cands]
    return out


async def main() -> None:
    conn = await connect()
    converted = 0
    dropped = 0
    try:
        for c in CONV:
            lesson_id = TITLE_TO_ID.get(c["lesson_title"])
            if not lesson_id:
                print(f"  SKIP (no lesson): {c['lesson_title']}"); continue
            blocks = await fetch_blocks(conn, lesson_id)
            idx = next((i for i, b in enumerate(blocks)
                        if b.get("id") == c["quiz_block_id"] and b.get("type") == "quiz"), None)
            if idx is None:
                print(f"  SKIP (quiz block not found): {c['lesson_title']}"); continue
            new_block = validate_and_normalise(c["new_block"])
            skel_before = [(b.get("id"), b.get("type")) for i, b in enumerate(blocks) if i != idx]
            blocks[idx] = new_block
            skel_after = [(b.get("id"), b.get("type")) for i, b in enumerate(blocks) if i != idx]
            assert skel_before == skel_after, "other blocks changed!"
            await write_blocks(conn, lesson_id, blocks)
            converted += 1
            print(f"  converted [{new_block['mode']}]: {c['lesson_title']}")

        for title, _track in DROP:
            lesson_id = TITLE_TO_ID.get(title)
            blocks = await fetch_blocks(conn, lesson_id)
            qidx = next((i for i, b in enumerate(blocks) if b.get("type") == "quiz"), None)
            if qidx is None:
                print(f"  SKIP drop (no quiz): {title}"); continue
            remove = {qidx}
            # walk back over md whitespace + the CYU heading immediately leading the quiz
            k = qidx - 1
            while k >= 0 and blocks[k].get("type") == "whitespace":
                remove.add(k); k -= 1
            if k >= 0 and blocks[k].get("type") == "heading" and \
                    (blocks[k].get("text") or "").strip().lower() == CHECK_UNDERSTANDING:
                remove.add(k)
                k -= 1
                while k >= 0 and blocks[k].get("type") == "whitespace":
                    remove.add(k); k -= 1
            new_blocks = [b for i, b in enumerate(blocks) if i not in remove]
            await write_blocks(conn, lesson_id, new_blocks)
            dropped += 1
            print(f"  dropped quiz + {len(remove) - 1} lead-in block(s): {title}")
    finally:
        await conn.close()
    print(f"\nDONE: {converted} conversions, {dropped} drops.")


if __name__ == "__main__":
    asyncio.run(main())
