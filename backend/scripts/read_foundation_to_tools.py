import asyncio
import json
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

HOST = os.environ["DATABASE__HOST"]
PORT = int(os.environ["DATABASE__PORT"])
USER = os.environ["DATABASE__USERNAME"]
PASSWORD = os.environ["DATABASE__PASSWORD"]
DBNAME = os.environ["DATABASE__NAME"]

MODULE_ID = "4e9f8450-5bbe-47f8-a014-ce3cc41f19d0"


async def main() -> None:
    conn = await asyncpg.connect(
        host=HOST, port=PORT, user=USER, password=PASSWORD, database=DBNAME, ssl="require"
    )
    try:
        module = await conn.fetchrow("SELECT * FROM modules WHERE id = $1", MODULE_ID)
        print("=== MODULE ===")
        print({k: v for k, v in dict(module).items()})

        track = await conn.fetchrow("SELECT * FROM tracks WHERE id = $1", module["track_id"])
        print("\n=== TRACK ===")
        print({k: v for k, v in dict(track).items()})

        lessons = await conn.fetch(
            "SELECT id, title, sort_order, content_blocks FROM lessons "
            "WHERE module_id = $1 ORDER BY sort_order",
            MODULE_ID,
        )
        print(f"\n=== LESSONS ({len(lessons)}) ===")
        out = []
        for les in lessons:
            blocks = (
                json.loads(les["content_blocks"])
                if isinstance(les["content_blocks"], str)
                else les["content_blocks"]
            )
            print(
                f"  [{les['sort_order']}] {les['title']}  (id={les['id']}, {len(blocks) if blocks else 0} blocks)"
            )
            out.append(
                {
                    "id": str(les["id"]),
                    "title": les["title"],
                    "sort_order": les["sort_order"],
                    "content_blocks": blocks,
                }
            )

        dump_path = os.path.join(os.path.dirname(__file__), "foundation_to_tools_LIVE.json")
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"\nDumped to {dump_path}")
    finally:
        await conn.close()


asyncio.run(main())
