"""Read-only pull of the 91 in-scope lessons (admin's 9 assigned tracks)."""

import asyncio
import json
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[2]  # .../backend
load_dotenv(BACKEND / ".env")
OUT_DIR = BACKEND.parent / "scratch_review" / "admin_content_qa_2026-07-20"
UID = "587f5667-2ddc-4b95-827c-09bcb92c5b7c"

QUERY = """
SELECT t.name AS track, t.required_level AS track_level, t.sort_order AS track_order,
       m.title AS module_title, m.id AS module_id, m.sort_order AS module_order,
       l.id AS lesson_id, l.title AS lesson_title, l.sort_order AS lesson_order,
       l.content_blocks
FROM user_lessons ul
JOIN lessons l ON l.id = ul.lesson_id
JOIN modules m ON m.id = l.module_id
JOIN tracks  t ON t.id = m.track_id
JOIN user_modules um ON um.user_id = ul.user_id AND um.module_id = m.id
JOIN user_tracks  ut ON ut.user_id = ul.user_id AND ut.track_id = t.id
WHERE ul.user_id = $1
ORDER BY t.sort_order, m.sort_order, l.sort_order
"""


async def main() -> None:
    conn = await asyncpg.connect(
        host=os.environ["DATABASE__HOST"],
        port=int(os.environ["DATABASE__PORT"]),
        user=os.environ["DATABASE__USERNAME"],
        password=os.environ["DATABASE__PASSWORD"],
        database=os.environ["DATABASE__NAME"],
        ssl="require",
    )
    try:
        rows = await conn.fetch(QUERY, UID)
    finally:
        await conn.close()

    out = []
    for r in rows:
        cb = r["content_blocks"]
        cb = json.loads(cb) if isinstance(cb, str) else cb
        out.append(
            {
                "track": r["track"],
                "track_level": r["track_level"],
                "track_order": r["track_order"],
                "module_title": r["module_title"],
                "module_id": str(r["module_id"]),
                "module_order": r["module_order"],
                "lesson_id": str(r["lesson_id"]),
                "lesson_title": r["lesson_title"],
                "lesson_order": r["lesson_order"],
                "content_blocks": cb or [],
            }
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "lessons_snapshot.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(out)} lessons to {OUT_DIR / 'lessons_snapshot.json'}")


asyncio.run(main())
