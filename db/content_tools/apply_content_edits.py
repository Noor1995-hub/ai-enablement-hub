# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Locator-based content-block editor for live lesson content. Matches
blocks by a unique text substring found within the lesson's own
content_blocks (not by hardcoded UUID) -- robust against re-fetching fresh
data each time. Safe-write pattern: fetch fresh -> dry-run -> write -> verify.

Write an "edits module" (plain .py file) with an EDITS dict:

    EDITS = {
        "Lesson Title": [
            ("replace", "some unique locator substring", "old text", "new text"),
            ("set_field", "locator", "text", "brand new full field value"),
            ("delete", "locator"),                                  # remove the block
            ("set_type_and_text", "locator", "kicker", "new text"), # change block type + text
            ("set_quiz_q0", "locator", {...new question dict...}),  # replace questions[0] wholesale
            ("set_try_it_yourself", "locator", task, material, steps, what_to_notice),
        ],
        ...
    }

`locator` just needs to be a substring unique to ONE block within that
lesson (searched via json.dumps of each block) -- it does not need to be
outside the text you're replacing.

Usage:
    uv run db/content_tools/apply_content_edits.py backend/.env titles.json edits.py out.json
    uv run db/content_tools/apply_content_edits.py backend/.env titles.json edits.py out.json --apply

`titles.json` is a JSON list of every lesson title the edits module touches
(order doesn't matter; extra titles are fetched but ignored).

To re-apply the SAME edits module to db/baseline/data/lessons.json after a
successful --apply, use sync_baseline.py (no DB connection needed).
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _edit_engine import EM, apply_one  # noqa: E402
from _env import dsn  # noqa: E402
import psycopg  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("env_file")
    parser.add_argument("titles_file", type=Path)
    parser.add_argument("edits_module", type=Path)
    parser.add_argument("out_file", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    titles = json.loads(args.titles_file.read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("edits_module", args.edits_module)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    EDITS = mod.EDITS

    with psycopg.connect(dsn(args.env_file)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, content_blocks FROM lessons WHERE title = ANY(%s)", (titles,))
        lessons = {title: {"id": str(lid), "blocks": blocks} for lid, title, blocks in cur.fetchall()}

        report = []
        for title, ledits in EDITS.items():
            if title not in lessons:
                raise SystemExit(f"lesson not found live: {title}")
            blocks = lessons[title]["blocks"]
            before = json.dumps(blocks, ensure_ascii=False)
            for e in ledits:
                apply_one(blocks, e)
            after = json.dumps(blocks, ensure_ascii=False)
            report.append((title, len(ledits), before != after, after.count(EM)))

        for title, n, changed, em_count in report:
            print(f"{title!r}: {n} edits applied, changed={changed}, em-dashes remaining={em_count}")

        args.out_file.write_text(
            json.dumps({t: lessons[t] for t in EDITS}, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Wrote proposed new content to {args.out_file}")

        if args.apply:
            for title in EDITS:
                cur.execute(
                    "UPDATE lessons SET content_blocks = %s::jsonb WHERE id = %s",
                    (json.dumps(lessons[title]["blocks"], ensure_ascii=False), lessons[title]["id"]),
                )
            conn.commit()
            print(f"Applied UPDATE for {len(EDITS)} lessons.")

            ids = [lessons[t]["id"] for t in EDITS]
            cur.execute("SELECT id, content_blocks FROM lessons WHERE id = ANY(%s)", (ids,))
            live = {str(lid): blocks for lid, blocks in cur.fetchall()}
            ok = True
            for title in EDITS:
                lid = lessons[title]["id"]
                if live[lid] != lessons[title]["blocks"]:  # structural compare, not string compare
                    print(f"VERIFY FAIL: {title}")
                    ok = False
            print("Verify OK for all lessons" if ok else "VERIFY FAILED for some lessons")
        else:
            print("Dry run only -- pass --apply to write to the live DB.")


if __name__ == "__main__":
    main()
