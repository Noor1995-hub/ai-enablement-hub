"""Parse a quiz answer-length-bias rewrite review file (the
`| # | Before | After |` markdown table format used in
scratch_review/quiz_answer_length_rewrites_*.md) into the rewrites.json input
format that apply_quiz_rewrites.py expects: a list of
{lesson_id, lesson, q_index, new_options, before_options_expected}.

Cross-references against the flagged.json this draft was written from (the
output of quiz_length_bias.py) to pull in lesson_id and to sanity-check the
"Before" column matches exactly -- prints a warning for any mismatch instead
of silently trusting the draft.

A question deliberately left as an exception (before == after for every row,
documented in prose rather than a "**Qn:" heading matched by this parser) is
naturally excluded from the output -- that's correct, not a bug: it means no
edit will be generated for it.

No third-party deps; runs with plain `python`.

Usage:
    python db/content_tools/parse_quiz_rewrite_draft.py draft.md flagged.json rewrites.json
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path


def main() -> None:
    draft_path = Path(sys.argv[1])
    flagged_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])

    flagged = json.loads(flagged_path.read_text(encoding="utf-8"))
    flagged_by_key = {(item["lesson"], item["q_index"]): item for item in flagged}

    lines = draft_path.read_text(encoding="utf-8").splitlines()

    row_re = re.compile(r'^\|\s*(\d+)\s*(\*\(correct\)\*)?\s*\|(.*)\|(.*)\|$')
    lesson_re = re.compile(r'^## (.+)$')
    q_re = re.compile(r'^\*\*Q(\d+):')

    lesson = None
    qnum = None
    rows: list[tuple[str, str, str, bool]] = []
    results = []

    def flush() -> None:
        nonlocal rows
        if qnum is not None and rows:
            key = (lesson, qnum - 1)
            if key not in flagged_by_key:
                print(f"WARNING: no flagged entry for {key}")
            else:
                item = flagged_by_key[key]
                ordered = sorted(rows, key=lambda r: int(r[0]))
                before_options = [r[1] for r in ordered]
                after_options = [r[2] for r in ordered]
                correct_rows = [i for i, r in enumerate(ordered) if r[3]]
                if before_options != item["options"]:
                    print(f"DRIFT MISMATCH for {key}: before={before_options} vs flagged={item['options']}")
                if len(correct_rows) != 1 or correct_rows[0] != item["correct"]:
                    print(f"CORRECT INDEX MISMATCH for {key}: table correct={correct_rows} vs flagged={item['correct']}")
                if after_options[item["correct"]] != item["options"][item["correct"]]:
                    print(f"CORRECT TEXT CHANGED for {key}!")
                results.append({
                    "lesson_id": item["lesson_id"],
                    "lesson": lesson,
                    "q_index": item["q_index"],
                    "new_options": after_options,
                    "before_options_expected": before_options,
                })
        rows = []

    for line in lines:
        m = lesson_re.match(line)
        if m:
            flush()
            lesson = m.group(1).strip()
            qnum = None
            continue
        m = q_re.match(line)
        if m:
            flush()
            qnum = int(m.group(1))
            continue
        m = row_re.match(line)
        if m:
            idx, correct_marker, before, after = m.groups()
            rows.append((idx, before.strip(), after.strip(), bool(correct_marker)))
    flush()

    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nParsed {len(results)} questions (source flagged file had {len(flagged)})")


if __name__ == "__main__":
    main()
