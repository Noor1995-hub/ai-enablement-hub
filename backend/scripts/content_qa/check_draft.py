"""Dry-run checks for lesson drafts, per docs/content/authoring-guide.md section 11.

The checks live in `src/services/lesson_qa.py`, shared with the lesson editor's
in-app Check and Save (B5); this file is the CLI over them.

The gate to run before every content write (General III, Claude II, and any
future authoring round). Input is a JSON array of lesson dicts, each with
`sort_order`, `title` and `content_blocks`.

Run from backend/:
    ./.venv/Scripts/python.exe scripts/content_qa/check_draft.py <draft.json> [--uuids]

Implements the guide's own checklist, which is NOT the same as the AI-pipeline
validator:
  - forbidden punctuation (em dash, en dash, ellipsis) in every text field
  - duplicate block / card / question / step / item ids
  - no quiz correct answer is the unique longest option
  - correct positions vary within a quiz
  - a "Check your understanding" heading immediately precedes every quiz
  - warn on any text field with more than two bold spans
  - sort bucketIds resolve to a real bucket; predict correctOptionId resolves
  - schema, via the repo's own validate_content_blocks

Deliberate divergence: authoring-guide.md section 5 says an EMPTY `blob_path`
renders a clean placeholder frame showing the alt text, and the editor uploads
into that same block, so shipping pre-coded image blocks is the intended
authoring pattern. `validate_content_blocks` requires a non-empty blob_path
because it was written for the AI revision pipeline, where inventing a storage
path is the failure mode. Empty-blob_path errors are therefore reported
separately as EXPECTED rather than as failures.

--uuids rewrites every block and nested id to a fresh uuid4 in place, keeping
bucketId and correctOptionId references intact.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # .../backend

from src.services.lesson_qa import check_blocks, text_fields  # noqa: E402


def check(lesson) -> tuple[list[str], list[str], list[str]]:
    """The script's historical entry point; the checks live in src/services/lesson_qa.py."""
    return check_blocks(lesson["content_blocks"])


def to_uuids(blocks) -> None:
    mapping: dict[str, str] = {}

    def assign(o):
        if isinstance(o, dict):
            if isinstance(o.get("id"), str):
                mapping[o["id"]] = str(uuid.uuid4())
            for v in o.values():
                assign(v)
        elif isinstance(o, list):
            for v in o:
                assign(v)

    def apply(o):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if (
                    k in ("id", "bucketId", "correctOptionId")
                    and isinstance(v, str)
                    and v in mapping
                ):
                    o[k] = mapping[v]
                else:
                    apply(v)
        elif isinstance(o, list):
            for v in o:
                apply(v)

    assign(blocks)
    apply(blocks)


def main() -> int:
    path = Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    rewrite = "--uuids" in sys.argv

    total_fails = 0
    for lesson in data:
        if rewrite:
            to_uuids(lesson["content_blocks"])
        fails, warns, expected = check(lesson)
        total_fails += len(fails)
        status = "OK  " if not fails else "FAIL"
        cb = lesson["content_blocks"]
        words = sum(len(v.split()) for _, v in text_fields(cb))
        print(f"{status} L{lesson['sort_order']} {lesson['title']}: blocks={len(cb)} words={words}")
        print(
            "      "
            + " > ".join(b["type"] + ("/" + b["mode"] if b.get("mode") else "") for b in cb)
        )
        for f in fails:
            print(f"      FAIL  {f}")
        for w in warns:
            print(f"      warn  {w}")
        for e in expected:
            print(f"      ok    {e}  (expected: authoring placeholder, guide section 5)")

    if rewrite:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nrewrote ids to uuid4 in {path.name}")

    print(f"\nTOTAL FAILURES: {total_fails}")
    return 1 if total_fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
