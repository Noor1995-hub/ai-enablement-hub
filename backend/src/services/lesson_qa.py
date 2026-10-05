"""House-style checks for lesson content (B5): authoring-guide.md section 11's
checklist, in one module.

The lesson editor runs these on Save and on Check (POST
/api/admin/lessons/{id}/check); `scripts/content_qa/check_draft.py` is the CLI
over the same functions, so the website and the script can never disagree.
Pure: no I/O.

The checks, which are NOT the same as the AI-pipeline validator:
  - forbidden punctuation (em dash, en dash, ellipsis) in every text field
  - duplicate block / card / question / step / item ids
  - no quiz correct answer is the unique longest option
  - correct positions vary within a quiz
  - a "Check your understanding" heading immediately precedes every quiz
  - more than two bold spans in one text field (bullet lead-ins excluded)
  - sort bucketIds resolve to a real bucket; predict correctOptionId resolves
  - schema, via validate_content_blocks

An EMPTY image `blob_path` is an authoring placeholder (guide section 5), so
validate_content_blocks' error for it is reported as `expected` / info.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from src.services.content_blocks_validation import check_house_style, validate_content_blocks

__all__ = ["Finding", "check_blocks", "check_lesson", "text_fields"]

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


def text_fields(obj: Any, path: str = "") -> list[tuple[str, str]]:
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


def collect_ids(blocks: Any) -> list[str]:
    found: list[str] = []

    def walk(o: Any) -> None:
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


def check_blocks(cb: list[Any]) -> tuple[list[str], list[str], list[str]]:
    """(fails, warns, expected): the authoring checklist, exactly as
    check_draft.py has always reported it."""
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


_BLOCK = re.compile(r"^(?:block)?\[(\d+)\]")


_DUPLICATE = re.compile(
    r"^block\[\d+\].*(?:contains a forbidden dash or ellipsis"
    r"|has more than two bold spans"
    r"|must be immediately preceded by a heading reading"
    r"|'correct' index is identical across every question"
    r"|\.correct is the unique longest option)$"
)


@dataclass(frozen=True)
class Finding:
    """One house-style finding, located for the editor ("block 4 · paragraph")."""

    severity: Literal["warning", "info"]
    block_index: int | None
    where: str
    message: str


def _locate(message: str, blocks: list[Any]) -> tuple[int | None, str]:
    """Messages name a block as `block[3]…` or a text path as `… in [3].text`."""
    head = message.rsplit(" in ", 1)[-1] if " in [" in message else message
    match = _BLOCK.match(head)
    if match is None:
        return None, "lesson"
    index = int(match.group(1))
    block = blocks[index] if index < len(blocks) else None
    block_type = block.get("type", "block") if isinstance(block, dict) else "block"
    return index, f"block {index + 1} · {block_type}"


def check_lesson(blocks: list[Any]) -> list[Finding]:
    """check_blocks as located findings. The script's fails and warns are
    warnings (never a block on save: most live lessons predate the nested-id
    rule); its EXPECTED bucket (an empty image blob_path) is info."""
    fails, warns, expected = check_blocks(blocks)
    # check_house_style repeats four rules the checklist already reports in its
    # own words (and the checklist's bold rule excludes bullet lead-ins). The
    # CLI has always printed both; the editor shows each problem once.
    fails = [message for message in fails if not _DUPLICATE.search(message)]
    findings: list[Finding] = []
    for severity, messages in (("warning", fails + warns), ("info", expected)):
        for message in messages:
            index, where = _locate(message, blocks)
            findings.append(Finding(severity, index, where, message))
    return findings
