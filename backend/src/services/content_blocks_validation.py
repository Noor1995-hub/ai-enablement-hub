from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

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
        errs += _validate_steps(where, block)
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
        errs += _require_str(cwhere, card_fields, "id")
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
        errs += _require_str(qwhere, question_fields, "id")
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


def _validate_steps(where: str, block: Mapping[str, object]) -> list[str]:
    steps = block.get("steps")
    if not isinstance(steps, list):
        return [f"{where}.steps must be a list"]
    errs: list[str] = []
    for j, step in enumerate(steps):
        swhere = f"{where}.steps[{j}]"
        if not isinstance(step, dict):
            errs.append(f"{swhere} must be an object")
            continue
        step_fields = cast(Mapping[str, object], step)
        errs += _require_str(swhere, step_fields, "id")
        errs += _require_str(swhere, step_fields, "label")
        errs += _require_str(swhere, step_fields, "text")
    return errs


def _validate_interactive(where: str, block: Mapping[str, object]) -> list[str]:
    mode = block.get("mode")
    if mode not in _INTERACTIVE_MODES:
        return [f"{where}.mode must be one of sort|predict|spot_the_flaw"]
    errs = _require_str(where, block, "prompt")
    if mode == "sort":
        errs += _validate_sort(where, block)
    elif mode == "predict":
        errs += _validate_predict(where, block)
    elif mode == "spot_the_flaw":
        errs += _validate_spot_the_flaw(where, block)
    return errs


def _validate_sort(where: str, block: Mapping[str, object]) -> list[str]:
    errs: list[str] = []
    buckets = block.get("buckets")
    bucket_ids: set[str] = set()
    if not isinstance(buckets, list):
        errs.append(f"{where}.buckets must be a list")
    else:
        for j, bucket in enumerate(buckets):
            bwhere = f"{where}.buckets[{j}]"
            if not isinstance(bucket, dict):
                errs.append(f"{bwhere} must be an object")
                continue
            bucket_fields = cast(Mapping[str, object], bucket)
            errs += _require_str(bwhere, bucket_fields, "id")
            errs += _require_str(bwhere, bucket_fields, "label")
            bucket_id = bucket.get("id")
            if isinstance(bucket_id, str) and bucket_id:
                bucket_ids.add(bucket_id)
    items = block.get("items")
    if not isinstance(items, list):
        errs.append(f"{where}.items must be a list")
    else:
        for j, item in enumerate(items):
            iwhere = f"{where}.items[{j}]"
            if not isinstance(item, dict):
                errs.append(f"{iwhere} must be an object")
                continue
            item_fields = cast(Mapping[str, object], item)
            errs += _require_str(iwhere, item_fields, "id")
            errs += _require_str(iwhere, item_fields, "text")
            errs += _require_str(iwhere, item_fields, "reason")
            bucket_id = item.get("bucketId")
            if not isinstance(bucket_id, str) or not bucket_id:
                errs.append(f"{iwhere}.bucketId must be a non-empty string")
            elif bucket_id not in bucket_ids:
                errs.append(f"{iwhere}.bucketId {bucket_id!r} does not match any bucket id")
    return errs


def _validate_predict(where: str, block: Mapping[str, object]) -> list[str]:
    errs: list[str] = []
    options = block.get("options")
    option_ids: set[str] = set()
    if not isinstance(options, list):
        errs.append(f"{where}.options must be a list")
    else:
        for j, option in enumerate(options):
            owhere = f"{where}.options[{j}]"
            if not isinstance(option, dict):
                errs.append(f"{owhere} must be an object")
                continue
            option_fields = cast(Mapping[str, object], option)
            errs += _require_str(owhere, option_fields, "id")
            errs += _require_str(owhere, option_fields, "label")
            errs += _require_str(owhere, option_fields, "reason")
            option_id = option.get("id")
            if isinstance(option_id, str) and option_id:
                option_ids.add(option_id)
    errs += _require_str(where, block, "correctOptionId")
    correct_option_id = block.get("correctOptionId")
    if (
        isinstance(correct_option_id, str)
        and correct_option_id
        and correct_option_id not in option_ids
    ):
        errs.append(f"{where}.correctOptionId {correct_option_id!r} does not match any option id")
    return errs


def _validate_spot_the_flaw(where: str, block: Mapping[str, object]) -> list[str]:
    errs = _require_str(where, block, "example")
    candidates = block.get("candidates")
    if not isinstance(candidates, list):
        errs.append(f"{where}.candidates must be a list")
        return errs
    for j, candidate in enumerate(candidates):
        cwhere = f"{where}.candidates[{j}]"
        if not isinstance(candidate, dict):
            errs.append(f"{cwhere} must be an object")
            continue
        candidate_fields = cast(Mapping[str, object], candidate)
        errs += _require_str(cwhere, candidate_fields, "id")
        errs += _require_str(cwhere, candidate_fields, "text")
        errs += _require_str(cwhere, candidate_fields, "reason")
        if not isinstance(candidate.get("isFlaw"), bool):
            errs.append(f"{cwhere}.isFlaw must be a bool")
    return errs


def _media_entry(block: dict[str, Any]) -> tuple[str, str] | None:
    """Classify one block's persisted media locator as a (kind, locator) pair,
    or None if the block carries no media at all.

    The kind is `"image"`, `"video:embed"`, or `"video:blob"` — never a bare
    `"video"` — so that a block whose `source` flips between embed and blob
    while keeping the same locator string is never mistaken for an unchanged
    block. A `video` with any other/missing `source` is `"video:invalid"` with
    an empty locator: it has no verifiable locator, so it must never silently
    compare equal to a real one. Likewise, if the locator field itself is
    missing or not a non-empty string, the entry is still returned with an
    empty locator rather than None, for the same reason.
    """
    btype = block.get("type")
    if btype == "image":
        locator = block.get("blob_path")
        return ("image", locator if isinstance(locator, str) and locator else "")
    if btype == "video":
        source = block.get("source")
        if source == "embed":
            locator = block.get("url")
            return ("video:embed", locator if isinstance(locator, str) and locator else "")
        if source == "blob":
            locator = block.get("blob_path")
            return ("video:blob", locator if isinstance(locator, str) and locator else "")
        return ("video:invalid", "")
    return None


def _media_by_id(blocks: object) -> dict[str, tuple[str, str]]:
    """The base's media (kind, locator) entries keyed by block id, so a
    proposal's media can be matched per block rather than as a bag of
    locators. Skips non-list input, non-dict entries, and blocks with no
    non-empty string `id` (their media cannot be matched by id at all)."""
    by_id: dict[str, tuple[str, str]] = {}
    if not isinstance(blocks, list):
        return by_id
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_id = block.get("id")
        if not isinstance(block_id, str) or not block_id:
            continue
        entry = _media_entry(cast(dict[str, Any], block))
        if entry is not None:
            by_id[block_id] = entry
    return by_id


def media_locators(blocks: object) -> list[tuple[str, str]]:
    """Every (media kind, PERSISTED locator) pair, in document order.

    The kind is `"image"`, `"video:embed"`, or `"video:blob"` — collapsing
    embed and blob videos into a bare `"video"` would let a proposal flip one
    into the other while keeping the same locator string unnoticed, which is
    exactly the kind of change `check_media_immutable` exists to catch. The
    persisted locator is `blob_path` for an image or an uploaded video and
    `url` for an embed video. An image/blob-video `url` is an ephemeral SAS
    stamped at read time (see services/media_blocks.py) and is deliberately
    ignored here — comparing it would flag every proposal.

    This is pure extraction; it validates nothing. Pair it with
    `check_media_immutable` for the immutability guarantee and with
    `validate_content_blocks` for structural validation — neither of those
    checks is a substitute for the other.
    """
    found: list[tuple[str, str]] = []
    if not isinstance(blocks, list):
        return found
    for block in blocks:
        if not isinstance(block, dict):
            continue
        entry = _media_entry(cast(dict[str, Any], block))
        if entry is not None and entry[1]:
            found.append(entry)
    return found


def check_media_immutable(base: object, proposed: object) -> list[str]:
    """Reject a proposal that adds an unverifiable media block or alters an
    existing one's kind/locator. Matches media PER BLOCK ID, not as a bag of
    locators. Returns human-readable error strings; empty means it is safe.

    A bag/multiset comparison cannot see a locator MOVE: swapping the
    `blob_path`s of two image blocks leaves the multiset of locators
    unchanged, yet every learner would now see the wrong image under each
    caption. It also cannot see an embed video reinterpreted as a blob video
    (or vice versa) pointing at the same string — the renderer would then
    resolve a URL as a storage path or vice versa. Matching by block id
    catches both.

    Dropping a media block is allowed — the agent may restructure a lesson and
    leave one out, and the admin sees that in the approval diff. Inventing a
    `blob_path` is not: it would point the learner renderer at a blob that does
    not exist, and the model has no way to know a real one.

    This is a media-only check. Callers are expected to also run
    `validate_content_blocks` — it catches every other structural problem
    (missing fields, unknown block types, and so on) that this function does
    not.
    """
    if not isinstance(proposed, list):
        return ["proposed content_blocks must be a list"]
    base_by_id = _media_by_id(base)
    errors: list[str] = []
    for block in proposed:
        if not isinstance(block, dict):
            continue
        entry = _media_entry(cast(dict[str, Any], block))
        if entry is None:
            continue
        block_id = block.get("id")
        if not isinstance(block_id, str) or not block_id:
            errors.append(
                f"proposal has a {entry[0]} block with no id; its media cannot be verified"
            )
            continue
        if base_by_id.get(block_id) != entry:
            errors.append(
                f"proposal adds or alters a {entry[0]} locator not present in "
                f"the lesson: {entry[1]!r} (block id {block_id!r})"
            )
    return errors
