"""Locator-based content-block edit engine, shared by apply_content_edits.py
(live DB) and sync_baseline.py (local snapshot file). No third-party deps,
so importing this never requires psycopg to be installed.

See apply_content_edits.py's module docstring for the EDITS-module format
and the full explanation of what a "locator" is.
"""
from __future__ import annotations
import json

EM = "—"  # em-dash, handy for edits modules that need it


def find_block_by_locator(blocks: list[dict], locator: str) -> dict:
    matches = [b for b in blocks if locator in json.dumps(b, ensure_ascii=False)]
    if len(matches) != 1:
        raise SystemExit(f"locator {locator!r} matched {len(matches)} blocks (need exactly 1)")
    return matches[0]


def do_replace(block: dict, locator: str, old: str, new: str) -> None:
    """Replace `old` with `new` in whichever single string field of `block`
    contains it -- covers paragraph/callout/kicker .text, card .title/.body,
    try_it_yourself .task/.material/.whatToNotice/.steps[].text, quiz
    .questions[].q/.explanation/.options[]."""
    found = 0
    fields = ["text", "title", "body", "task", "material", "whatToNotice", "prompt", "example"]
    for f in fields:
        if f in block and isinstance(block[f], str) and old in block[f]:
            n = block[f].count(old)
            if n != 1:
                raise SystemExit(f"{old!r} occurs {n} times in block {block.get('id')}.{f}")
            block[f] = block[f].replace(old, new, 1)
            found += 1
    if block.get("type") == "card_group":
        for card in block.get("cards", []):
            for f in ("title", "body"):
                if f in card and old in card[f]:
                    n = card[f].count(old)
                    if n != 1:
                        raise SystemExit(f"{old!r} occurs {n} times in a card.{f}")
                    card[f] = card[f].replace(old, new, 1)
                    found += 1
    if block.get("type") == "try_it_yourself":
        for step in block.get("steps", []):
            if "text" in step and old in step["text"]:
                n = step["text"].count(old)
                if n != 1:
                    raise SystemExit(f"{old!r} occurs {n} times in a try_it_yourself step")
                step["text"] = step["text"].replace(old, new, 1)
                found += 1
    if block.get("type") == "quiz":
        for q in block.get("questions", []):
            for f in ("q", "explanation"):
                if f in q and old in q[f]:
                    q[f] = q[f].replace(old, new, 1)
                    found += 1
            for i, opt in enumerate(q.get("options", [])):
                if old in opt:
                    q["options"][i] = opt.replace(old, new, 1)
                    found += 1
    if found != 1:
        raise SystemExit(f"replace old={old!r} matched {found} fields in block {block.get('id')} (locator {locator!r})")


def apply_one(blocks: list[dict], e: tuple) -> list[dict]:
    kind = e[0]
    if kind == "replace":
        _, locator, old, new = e
        do_replace(find_block_by_locator(blocks, locator), locator, old, new)
    elif kind == "set_field":
        _, locator, field, new_val = e
        find_block_by_locator(blocks, locator)[field] = new_val
    elif kind == "delete":
        _, locator = e
        blocks.remove(find_block_by_locator(blocks, locator))
    elif kind == "set_type_and_text":
        _, locator, new_type, new_text = e
        b = find_block_by_locator(blocks, locator)
        b["type"], b["text"] = new_type, new_text
    elif kind == "set_quiz_q0":
        _, locator, new_q = e
        find_block_by_locator(blocks, locator)["questions"][0] = new_q
    elif kind == "set_try_it_yourself":
        _, locator, task, material, steps, what_to_notice = e
        b = find_block_by_locator(blocks, locator)
        b["task"], b["material"], b["steps"], b["whatToNotice"] = task, material, steps, what_to_notice
    else:
        raise SystemExit(f"unknown edit kind {kind!r}")
    return blocks
