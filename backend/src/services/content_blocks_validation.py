from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import cast

__all__ = [
    "KNOWN_BLOCK_TYPES",
    "check_media_immutable",
    "media_locators",
    "validate_content_blocks",
]

KNOWN_BLOCK_TYPES = {
    "heading",
    "paragraph",
    "callout",
    "kicker",
    "card_group",
    "quiz",
    "question",
    "whitespace",
    "interactive",
    "try_it_yourself",
    "image",
    "video",
}
_INTERACTIVE_MODES = {"sort", "predict", "spot_the_flaw"}
_WHITESPACE_SIZES = {"sm", "md", "lg"}


def validate_content_blocks(blocks: object) -> list[str]:
    """Structurally validate a proposed content_blocks array against the
    frontend union in frontend/src/types/contentBlocks.ts. Returns a list of
    human-readable error strings; an empty list means the array is valid.

    Purely structural. It does NOT enforce media immutability (that a proposal
    must not add or alter image/video blob_paths) — that lives in
    `check_media_immutable` below.
    """
    if not isinstance(blocks, list):
        return ["content_blocks must be a list"]
    errors: list[str] = []
    for i, block in enumerate(blocks):
        errors.extend(_validate_block(i, block))
    return errors


def _validate_block(i: int, block: object) -> list[str]:
    where = f"block[{i}]"
    if not isinstance(block, dict):
        return [f"{where} must be an object"]
    errs: list[str] = []
    block_id = block.get("id")
    if not isinstance(block_id, str) or not block_id:
        errs.append(f"{where} missing non-empty string 'id'")
    btype = block.get("type")
    if not isinstance(btype, str) or btype not in KNOWN_BLOCK_TYPES:
        errs.append(f"{where} has unknown type {btype!r}")
        return errs
    errs.extend(_validate_fields(where, btype, cast(Mapping[str, object], block)))
    return errs


def _require_str(where: str, block: Mapping[str, object], field: str) -> list[str]:
    value = block.get(field)
    if not isinstance(value, str) or not value:
        return [f"{where}.{field} must be a non-empty string"]
    return []


def _validate_fields(where: str, btype: str, block: Mapping[str, object]) -> list[str]:
    errs: list[str] = []
    if btype in ("paragraph", "callout", "kicker"):
        errs += _require_str(where, block, "text")
    elif btype == "question":
        errs += _require_str(where, block, "prompt")
    elif btype == "heading":
        errs += _require_str(where, block, "text")
        if block.get("level") not in (1, 2, 3):
            errs.append(f"{where}.level must be 1, 2, or 3")
    elif btype == "whitespace":
        if block.get("size") not in _WHITESPACE_SIZES:
            errs.append(f"{where}.size must be one of sm|md|lg")
    elif btype == "card_group":
        errs += _validate_card_group(where, block)
    elif btype == "quiz":
        errs += _validate_quiz(where, block)
    elif btype == "interactive":
        errs += _validate_interactive(where, block)
    elif btype == "try_it_yourself":
        for field in ("task", "material", "whatToNotice"):
            errs += _require_str(where, block, field)
        if not isinstance(block.get("steps"), list):
            errs.append(f"{where}.steps must be a list")
    elif btype == "image":
        errs += _require_str(where, block, "blob_path")
        errs += _require_str(where, block, "alt")
    elif btype == "video":
        source = block.get("source")
        if source == "embed":
            errs += _require_str(where, block, "url")
        elif source == "blob":
            errs += _require_str(where, block, "blob_path")
        else:
            errs.append(f"{where}.source must be 'embed' or 'blob'")
    return errs


def _validate_card_group(where: str, block: Mapping[str, object]) -> list[str]:
    cards = block.get("cards")
    if not isinstance(cards, list) or not cards:
        return [f"{where}.cards must be a non-empty list"]
    errs: list[str] = []
    for j, card in enumerate(cards):
        cwhere = f"{where}.cards[{j}]"
        if not isinstance(card, dict):
            errs.append(f"{cwhere} must be an object")
            continue
        card_fields = cast(Mapping[str, object], card)
        errs += _require_str(cwhere, card_fields, "title")
        errs += _require_str(cwhere, card_fields, "body")
    return errs


def _validate_quiz(where: str, block: Mapping[str, object]) -> list[str]:
    questions = block.get("questions")
    if not isinstance(questions, list) or not questions:
        return [f"{where}.questions must be a non-empty list"]
    errs: list[str] = []
    for j, question in enumerate(questions):
        qwhere = f"{where}.questions[{j}]"
        if not isinstance(question, dict):
            errs.append(f"{qwhere} must be an object")
            continue
        question_fields = cast(Mapping[str, object], question)
        errs += _require_str(qwhere, question_fields, "q")
        errs += _require_str(qwhere, question_fields, "explanation")
        options = question.get("options")
        if (
            not isinstance(options, list)
            or not options
            or not all(isinstance(o, str) for o in options)
        ):
            errs.append(f"{qwhere}.options must be a non-empty list of strings")
            continue
        correct = question.get("correct")
        if (
            not isinstance(correct, int)
            or isinstance(correct, bool)
            or not (0 <= correct < len(options))
        ):
            errs.append(f"{qwhere}.correct must be an index into options")
    return errs


def _validate_interactive(where: str, block: Mapping[str, object]) -> list[str]:
    mode = block.get("mode")
    if mode not in _INTERACTIVE_MODES:
        return [f"{where}.mode must be one of sort|predict|spot_the_flaw"]
    errs = _require_str(where, block, "prompt")
    if mode == "sort":
        for field in ("buckets", "items"):
            if not isinstance(block.get(field), list):
                errs.append(f"{where}.{field} must be a list")
    elif mode == "predict":
        if not isinstance(block.get("options"), list):
            errs.append(f"{where}.options must be a list")
        errs += _require_str(where, block, "correctOptionId")
    elif mode == "spot_the_flaw":
        errs += _require_str(where, block, "example")
        if not isinstance(block.get("candidates"), list):
            errs.append(f"{where}.candidates must be a list")
    return errs


def media_locators(blocks: object) -> list[tuple[str, str]]:
    """Every (block type, PERSISTED media locator) pair, in document order.

    The persisted locator is `blob_path` for an image or an uploaded video and
    `url` for an embed video. An image/blob-video `url` is an ephemeral SAS
    stamped at read time (see services/media_blocks.py) and is deliberately
    ignored here — comparing it would flag every proposal.
    """
    found: list[tuple[str, str]] = []
    if not isinstance(blocks, list):
        return found
    for block in blocks:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        locator: object = None
        if btype == "image":
            locator = block.get("blob_path")
        elif btype == "video":
            locator = block.get("url") if block.get("source") == "embed" else block.get("blob_path")
        if isinstance(btype, str) and isinstance(locator, str) and locator:
            found.append((btype, locator))
    return found


def check_media_immutable(base: object, proposed: object) -> list[str]:
    """Reject a proposal that ADDS a media block or ALTERS an existing one's
    locator. Returns human-readable error strings; empty means it is safe.

    Dropping a media block is allowed — the agent may restructure a lesson and
    leave one out, and the admin sees that in the approval diff. Inventing a
    `blob_path` is not: it would point the learner renderer at a blob that does
    not exist, and the model has no way to know a real one.
    """
    base_counts = Counter(media_locators(base))
    errors: list[str] = []
    for (btype, locator), count in Counter(media_locators(proposed)).items():
        if count > base_counts[(btype, locator)]:
            errors.append(
                f"proposal adds or alters a {btype} locator not present in the lesson: {locator!r}"
            )
    return errors
