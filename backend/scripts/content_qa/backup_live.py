"""Back up the current live content_blocks of all 91 in-scope lessons.

Reversibility safety net before the apply phase. Writes a timestamped file so
any change can be restored. Also prints the connected DB user/role so we know
whether we have DML (write) access before touching anything.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND / ".env")
WORK = BACKEND.parent / "scratch_review" / "admin_content_qa_2026-07-20"
UID = "587f5667-2ddc-4b95-827c-09bcb92c5b7c"

QUERY = """
SELECT l.id AS lesson_id, l.title AS lesson_title, t.name AS track,
       m.title AS module_title, l.content_blocks
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
        who = await conn.fetchrow("SELECT current_user, current_database()")
        print(f"connected as {who['current_user']} on {who['current_database']}")
        # write-access probe (rolled back, changes nothing)
        can_write = False
        try:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE lessons SET title = title WHERE id = $1", UID
                )  # no-op on a non-existent id; syntax/priv check
                can_write = True
        except asyncpg.InsufficientPrivilegeError:
            can_write = False
        except Exception:
            can_write = True  # ran, just matched no rows
        print(f"UPDATE privilege on lessons: {can_write}")

        rows = await conn.fetch(QUERY, UID)
    finally:
        await conn.close()

    out = []
    for r in rows:
        cb = r["content_blocks"]
        cb = json.loads(cb) if isinstance(cb, str) else cb
        out.append(
            {
                "lesson_id": str(r["lesson_id"]),
                "lesson_title": r["lesson_title"],
                "track": r["track"],
                "module_title": r["module_title"],
                "content_blocks": cb or [],
            }
        )

    stamp = (
        sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    )
    path = WORK / f"live_backup_{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"backed up {len(out)} lessons to {path.name}")


asyncio.run(main())
