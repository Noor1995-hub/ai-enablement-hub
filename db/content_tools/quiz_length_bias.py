# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Quantify the quiz answer-length bias (correct answer is the unique-longest
option) for one or more tracks, against LIVE data. Read-only report.

Usage:
    uv run db/content_tools/quiz_length_bias.py backend/.env flagged.json --tracks "Claude" "Confluence"

Fixing a flagged question: lengthen the WRONG options to be comparable to the
correct one (don't shorten the correct answer -- it may need that length/
nuance). Keep each distractor clearly wrong but plausible. Never touch the
correct answer's text or index; never touch a quiz block for any other
reason. See db/content_tools/apply_content_edits.py to apply the rewrites,
using ("set_field", locator, "options", [...]) per flagged question -- or
simpler, patch quiz_block["questions"][q_index]["options"] directly by
lesson id (see scratch_review/quiz_answer_length_rewrites_2026-07-15.md for
a full worked example of the review-file format used for the General I/II
pass).
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
    parser.add_argument("--tracks", nargs="+", required=True)
    args = parser.parse_args()

    with psycopg.connect(dsn(args.env_file)) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.name, l.id, l.title, l.content_blocks
            FROM lessons l JOIN modules m ON l.module_id = m.id JOIN tracks t ON m.track_id = t.id
            WHERE t.name = ANY(%s)
            ORDER BY t.name, m.sort_order, l.sort_order
        """, (args.tracks,))
        rows = cur.fetchall()

    total_q = 0
    flagged = []
    for track, lesson_id, lesson_title, blocks in rows:
        for b in blocks:
            if b.get("type") != "quiz":
                continue
            for qi, q in enumerate(b.get("questions", [])):
                total_q += 1
                opts = q["options"]
                lens = [len(o) for o in opts]
                correct_len = lens[q["correct"]]
                max_len = max(lens)
                if correct_len == max_len and lens.count(max_len) == 1:
                    flagged.append({
                        "track": track, "lesson": lesson_title, "lesson_id": str(lesson_id),
                        "q_index": qi, "q": q["q"], "options": opts, "correct": q["correct"],
                    })

    n = len(flagged)
    print(f"Tracks: {args.tracks}")
    print(f"Total quiz questions: {total_q}")
    if total_q:
        print(f"Correct answer is unique longest option: {n} ({100 * n / total_q:.0f}%)")
    args.out_file.write_text(json.dumps(flagged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {n} flagged questions to {args.out_file}")


if __name__ == "__main__":
    main()
