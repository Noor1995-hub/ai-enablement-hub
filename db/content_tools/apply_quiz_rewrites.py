# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Apply quiz answer-length-bias rewrites (options only) to live lesson
content, keyed by (lesson_id, q_index) -- the pattern described in
quiz_length_bias.py's docstring and used for the General I/II round.

rewrites.json is a list of {lesson_id, lesson, q_index, new_options}.
Drift guard: refetches fresh content_blocks and asserts the live question's
correct-answer text is unchanged and its index is untouched before patching
options -- if the live data drifted since the rewrite was drafted, this
aborts loudly instead of silently overwriting something new.

Usage:
    uv run db/content_tools/apply_quiz_rewrites.py backend/.env rewrites.json out.json
    uv run db/content_tools/apply_quiz_rewrites.py backend/.env rewrites.json out.json --apply
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
    parser.add_argument("rewrites_file", type=Path)
    parser.add_argument("out_file", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    rewrites = json.loads(args.rewrites_file.read_text(encoding="utf-8"))
    ids = sorted({r["lesson_id"] for r in rewrites})

    with psycopg.connect(dsn(args.env_file)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, title, content_blocks FROM lessons WHERE id = ANY(%s)", (ids,))
        lessons = {str(lid): {"title": title, "blocks": blocks} for lid, title, blocks in cur.fetchall()}

        touched_ids = set()
        for r in rewrites:
            lid = r["lesson_id"]
            if lid not in lessons:
                raise SystemExit(f"lesson not found live: {r['lesson']} ({lid})")
            blocks = lessons[lid]["blocks"]
            quiz_blocks = [b for b in blocks if b.get("type") == "quiz"]
            if len(quiz_blocks) != 1:
                raise SystemExit(f"expected exactly 1 quiz block in {r['lesson']!r}, found {len(quiz_blocks)}")
            questions = quiz_blocks[0]["questions"]
            if r["q_index"] >= len(questions):
                raise SystemExit(f"q_index {r['q_index']} out of range for {r['lesson']!r}")
            q = questions[r["q_index"]]
            old_options = q["options"]
            correct_i = q["correct"]
            new_options = r["new_options"]
            expected_before = r["before_options_expected"]
            if old_options != expected_before:
                raise SystemExit(
                    f"DRIFT: live options differ from what was drafted against, "
                    f"in {r['lesson']!r} q{r['q_index']} -- live data changed since drafting, aborting"
                )
            if len(new_options) != len(old_options):
                raise SystemExit(f"option count changed for {r['lesson']!r} q{r['q_index']}")
            if new_options[correct_i] != old_options[correct_i]:
                raise SystemExit(
                    f"DRIFT: correct-answer text differs from what was drafted against, "
                    f"in {r['lesson']!r} q{r['q_index']} -- live data changed since drafting, aborting"
                )
            q["options"] = new_options
            touched_ids.add(lid)

        report = []
        for lid in touched_ids:
            report.append(lessons[lid]["title"])
        for title in sorted(report):
            print(f"{title!r}: patched")

        args.out_file.write_text(
            json.dumps({lessons[lid]["title"]: lessons[lid] for lid in touched_ids}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Wrote proposed new content to {args.out_file}")

        if args.apply:
            for lid in touched_ids:
                cur.execute(
                    "UPDATE lessons SET content_blocks = %s::jsonb WHERE id = %s",
                    (json.dumps(lessons[lid]["blocks"], ensure_ascii=False), lid),
                )
            conn.commit()
            print(f"Applied UPDATE for {len(touched_ids)} lessons.")

            cur.execute("SELECT id, content_blocks FROM lessons WHERE id = ANY(%s)", (list(touched_ids),))
            live = {str(lid): blocks for lid, blocks in cur.fetchall()}
            ok = True
            for lid in touched_ids:
                if live[lid] != lessons[lid]["blocks"]:  # structural compare, not string compare
                    print(f"VERIFY FAIL: {lessons[lid]['title']}")
                    ok = False
            print("Verify OK for all lessons" if ok else "VERIFY FAILED for some lessons")
        else:
            print("Dry run only -- pass --apply to write to the live DB.")


if __name__ == "__main__":
    main()
