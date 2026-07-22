"""Apply the rewritten 'You're ready' lesson to the live DB.

Backs up the live row first, updates only title/content_blocks, then re-validates the read-back.
Keeps the EXISTING title (only content_blocks is rewritten).
"""

import asyncio
import json
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

conn_kwargs = dict(
    host=os.environ["DATABASE__HOST"],
    port=int(os.environ["DATABASE__PORT"]),
    user=os.environ["DATABASE__USERNAME"],
    password=os.environ["DATABASE__PASSWORD"],
    database=os.environ["DATABASE__NAME"],
    ssl="require",
)

LESSON_ID = "a4e1e842-6bf1-4225-a1eb-e3782193b2e0"
DRAFT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "scratch_review",
        "claude_cowork",
        "drafts",
        "foundation_to_tools_REWRITE.json",
    )
)
BACKUP_PATH = os.path.join(os.path.dirname(__file__), "foundation_to_tools_DBBACKUP.json")

FORBIDDEN = {"em dash": "—", "en dash": "–", "ellipsis": "…"}


def walk_strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v)
    elif isinstance(obj, str):
        yield obj


def collect_ids(obj, out):
    if isinstance(obj, dict):
        if "id" in obj:
            out.append(obj["id"])
        for v in obj.values():
            collect_ids(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_ids(v, out)


def validate(blocks, label):
    problems = []
    for s in walk_strings(blocks):
        for name, ch in FORBIDDEN.items():
            if ch in s:
                problems.append(f"{name}: {s[:50]!r}")
    ids = []
    collect_ids(blocks, ids)
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        problems.append(f"duplicate ids: {dupes}")
    for b in blocks:
        if b.get("type") == "image" and "url" in b:
            problems.append("image has stray url")
    print(f"[{label}] blocks={len(blocks)} problems={problems if problems else 'none'}")
    return not problems


async def main() -> None:
    with open(DRAFT_PATH, encoding="utf-8") as f:
        draft = json.load(f)[0]
    new_blocks = draft["content_blocks"]

    if not validate(new_blocks, "draft dry-run"):
        raise SystemExit("draft failed validation; aborting")

    conn = await asyncpg.connect(**conn_kwargs)
    try:
        row = await conn.fetchrow(
            "SELECT id, title, content_blocks FROM lessons WHERE id = $1", LESSON_ID
        )
        if row is None:
            raise SystemExit("lesson not found")

        existing_title = row["title"]
        existing_blocks = row["content_blocks"]
        if isinstance(existing_blocks, str):
            existing_blocks = json.loads(existing_blocks)

        # Back up the live row before touching it.
        with open(BACKUP_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"id": str(row["id"]), "title": existing_title, "content_blocks": existing_blocks},
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"backed up live row -> {BACKUP_PATH} ({len(existing_blocks)} blocks)")
        print(f"keeping existing title: {existing_title!r}")

        # Apply: keep existing title, replace content_blocks only.
        await conn.execute(
            "UPDATE lessons SET content_blocks = $1::jsonb WHERE id = $2",
            json.dumps(new_blocks),
            LESSON_ID,
        )
        print("UPDATE applied.")

        # Read back and validate.
        back = await conn.fetchrow(
            "SELECT title, content_blocks FROM lessons WHERE id = $1", LESSON_ID
        )
        back_blocks = back["content_blocks"]
        if isinstance(back_blocks, str):
            back_blocks = json.loads(back_blocks)
        ok = validate(back_blocks, "read-back")
        types = [b.get("type") for b in back_blocks]
        print(f"read-back title: {back['title']!r}")
        print(f"read-back types: {types}")
        if not ok:
            raise SystemExit("read-back FAILED validation")
        if back_blocks != new_blocks:
            raise SystemExit("read-back does not match pushed blocks")
        print("\nSUCCESS: read-back matches pushed draft, validation clean.")
    finally:
        await conn.close()


asyncio.run(main())
