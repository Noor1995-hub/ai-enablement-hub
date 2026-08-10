"""Dry-run checks for lesson drafts, per docs/content/authoring-guide.md section 11.

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
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))  # .../backend/src

from services.content_blocks_validation import (  # noqa: E402
    check_house_style,
    validate_content_blocks,
)

FORBIDDEN = {"—": "em dash", "–": "en dash", "…": "ellipsis"}
BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
BULLET_LEAD_IN = re.compile(r"^- \*\*.+?\.\*\*", re.MULTILINE)
SKIP_KEYS = {
    "id",
    "type",
    "mode",
    "level",
    "size",
    "correct",
    "isFlaw",
    "bucketId",
    "correctOptionId",
    "blob_path",
}
EMPTY_BLOB = re.compile(r"^block\[\d+\]\.blob_path must be a non-empty string$")


def text_fields(obj, path="") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in SKIP_KEYS:
                continue
            out += text_fields(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += text_fields(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        out.append((path, obj))
    return out


def collect_ids(blocks) -> list[str]:
    found: list[str] = []

    def walk(o):
        if isinstance(o, dict):
            if "id" in o and isinstance(o["id"], str):
                found.append(o["id"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(blocks)
    return found


def bold_count(text: str) -> int:
    lead_ins = {m.group() for m in BULLET_LEAD_IN.finditer(text)}
    total = 0
    for m in BOLD.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        chunk = text[line_start : m.end()]
        if any(chunk.endswith(li) or li in chunk for li in lead_ins) and chunk.lstrip().startswith(
            "- **"
        ):
            continue
        total += 1
    return total


def check(lesson) -> tuple[list[str], list[str], list[str]]:
    cb = lesson["content_blocks"]
    fails: list[str] = []
    warns: list[str] = []
    expected: list[str] = []

    for e in validate_content_blocks(cb):
        (expected if EMPTY_BLOB.match(e) else fails).append(e)
    fails += check_house_style([], cb)

    for path, value in text_fields(cb):
        for ch, name in FORBIDDEN.items():
            if ch in value:
                fails.append(f"{name} in {path}")
        if bold_count(value) > 2:
            warns.append(f"{bold_count(value)} bold spans in {path}")

    ids = collect_ids(cb)
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        fails.append(f"duplicate ids: {sorted(dupes)}")

    for i, b in enumerate(cb):
        if b.get("type") == "quiz":
            prev = cb[i - 1] if i else None
            if not (
                prev
                and prev.get("type") == "heading"
                and prev.get("text") == "Check your understanding"
            ):
                fails.append(
                    f"block[{i}] quiz not preceded by a 'Check your understanding' heading"
                )
            positions = [q.get("correct") for q in b.get("questions", [])]
            if len(set(positions)) == 1 and len(positions) > 1:
                fails.append(f"block[{i}] quiz correct position never varies ({positions})")
            for q in b.get("questions", []):
                lengths = [len(o) for o in q.get("options", [])]
                c = q.get("correct")
                in_range = lengths and isinstance(c, int) and 0 <= c < len(lengths)
                if in_range and lengths[c] == max(lengths) and lengths.count(max(lengths)) == 1:
                    fails.append(f"block[{i}] {q.get('id')} correct is the unique longest option")
        if b.get("type") == "interactive":
            if b.get("mode") == "sort":
                bucket_ids = {x.get("id") for x in b.get("buckets", [])}
                for item in b.get("items", []):
                    if item.get("bucketId") not in bucket_ids:
                        fails.append(f"block[{i}] item {item.get('id')} has unresolved bucketId")
            if b.get("mode") == "predict":
                option_ids = {x.get("id") for x in b.get("options", [])}
                if b.get("correctOptionId") not in option_ids:
                    fails.append(f"block[{i}] correctOptionId does not resolve")

    return fails, warns, expected


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
