# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Fetch lessons fresh from the live Azure DB -- by track name(s), and/or an
explicit title list. Read-only. Reads DB creds from backend/.env at runtime;
never persists the password.

Usage:
    uv run db/content_tools/fetch_lessons.py backend/.env out.json --tracks "Claude" "Confluence"
    uv run db/content_tools/fetch_lessons.py backend/.env out.json --titles titles.json
    uv run db/content_tools/fetch_lessons.py backend/.env out.json --all   # every lesson, every track
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _env import dsn  # noqa: E402
import psycopg  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("env_file")
    parser.add_argument("out_file", type=Path)
    parser.add_argument("--tracks", nargs="*", default=None, help="track names, e.g. Claude Confluence")
    parser.add_argument("--titles", type=Path, default=None, help="JSON file: a list of exact lesson titles")
    parser.add_argument("--all", action="store_true", help="fetch every lesson in every track")
    args = parser.parse_args()

    if not (args.tracks or args.titles or args.all):
        sys.exit("specify --tracks, --titles, or --all")

    with psycopg.connect(dsn(args.env_file)) as conn:
        cur = conn.cursor()
        if args.all:
            cur.execute("""
                SELECT t.name, m.title, l.id, l.title, l.content_blocks
                FROM lessons l JOIN modules m ON l.module_id = m.id JOIN tracks t ON m.track_id = t.id
                ORDER BY t.name, m.sort_order, l.sort_order
            """)
        elif args.tracks:
            cur.execute("""
                SELECT t.name, m.title, l.id, l.title, l.content_blocks
                FROM lessons l JOIN modules m ON l.module_id = m.id JOIN tracks t ON m.track_id = t.id
                WHERE t.name = ANY(%s)
                ORDER BY t.name, m.sort_order, l.sort_order
            """, (args.tracks,))
        else:
            titles = json.loads(args.titles.read_text(encoding="utf-8"))
            cur.execute("""
                SELECT t.name, m.title, l.id, l.title, l.content_blocks
                FROM lessons l JOIN modules m ON l.module_id = m.id JOIN tracks t ON m.track_id = t.id
                WHERE l.title = ANY(%s)
                ORDER BY t.name, m.sort_order, l.sort_order
            """, (titles,))
        rows = cur.fetchall()

    result = [
        {"track": track, "module": module, "id": str(lid), "title": title, "content_blocks": blocks}
        for track, module, lid, title, blocks in rows
    ]
    args.out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(result)} lessons to {args.out_file}")


if __name__ == "__main__":
    main()
