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

# Get started (Matthias-written) + Use it well (first lesson)
MODULES = {
    "Get started": "2a6a37fd-c325-40fc-b13b-301922b40a87",
}


def render_block(b: dict) -> str:
    t = b.get("type")
    if t == "heading":
        return f"\n## [{b.get('level')}] {b.get('text')}"
    if t in ("paragraph", "callout", "kicker", "question"):
        return f"[{t}] {b.get('text') or b.get('prompt')}"
    if t == "card_group":
        cards = "\n".join(f"   - {c.get('title')}: {c.get('body')}" for c in b.get("cards", []))
        return f"[card_group]\n{cards}"
    if t == "quiz":
        return f"[quiz] {len(b.get('questions', []))} questions"
    if t == "whitespace":
        return f"[whitespace {b.get('size')}]"
    if t == "image":
        return f"[image blob_path={b.get('blob_path')!r} alt={b.get('alt')!r} caption={b.get('caption')!r} width={b.get('width')}]"
    if t == "try_it_yourself":
        return f"[try_it_yourself task={b.get('task')!r}]"
    if t == "interactive":
        return f"[interactive {b.get('mode')}]"
    return f"[{t}] {json.dumps(b)[:200]}"


async def main() -> None:
    conn = await asyncpg.connect(**conn_kwargs)
    try:
        for name, mid in MODULES.items():
            lessons = await conn.fetch(
                "SELECT title, sort_order, content_blocks FROM lessons WHERE module_id=$1 ORDER BY sort_order",
                mid,
            )
            print(f"\n\n############ MODULE: {name} ############")
            for les in lessons:
                blocks = les["content_blocks"]
                if isinstance(blocks, str):
                    blocks = json.loads(blocks)
                print(f"\n===== LESSON: {les['title']} ({len(blocks)} blocks) =====")
                for b in blocks:
                    print(render_block(b))
    finally:
        await conn.close()


asyncio.run(main())
