from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, cast

__all__ = [
    "KNOWN_BLOCK_TYPES",
    "check_house_style",
    "check_media_immutable",
    "media_locators",
    "normalise_nested_ids",
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
# Every nested list whose dict entries carry their own `id` — the lists the
# validators below check and `normalise_nested_ids` back-fills. A quiz
# question's `options` is a list of plain strings, not dicts; the "entry is a
# dict" guard in the normaliser is what keeps those strings as strings.
_NESTED_ID_LISTS = ("cards", "questions", "steps", "buckets", "items", "options", "candidates")


def validate_content_blocks(blocks: object) -> list[str]:
    """Structurally validate a proposed content_blocks array against the
    frontend union in frontend/src/types/contentBlocks.ts. Returns a list of
    human-readable error strings; an empty list means the array is valid.

    Ids must be unique — top-level block ids across the whole array, nested
    item ids within their own list. Duplicates pass every per-field check but
    collide on `key={...}` in the learner renderer once approved, and a
    duplicated media block would even slip past `check_media_immutable` (both
    copies match the base entry for that id).

    Purely structural. It does NOT enforce media immutability (that a proposal
    must not add or alter image/video blob_paths) — that lives in
    `check_media_immutable` below.
    """
    if not isinstance(blocks, list):
        return ["content_blocks must be a list"]
    errors: list[str] = []
    seen_ids: set[str] = set()
    for i, block in enumerate(blocks):
        errors.extend(_validate_block(i, block, seen_ids))
    return errors


def _validate_block(i: int, block: object, seen_ids: set[str]) -> list[str]:
    where = f"block[{i}]"
    if not isinstance(block, dict):
        return [f"{where} must be an object"]
    errs: list[str] = []
    block_id = block.get("id")
    if not isinstance(block_id, str) or not block_id:
        errs.append(f"{where} missing non-empty string 'id'")
    elif block_id in seen_ids:
        errs.append(f"{where} duplicate id {block_id!r}")
    else:
        seen_ids.add(block_id)
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


def _require_unique_id(where: str, item: Mapping[str, object], seen: set[str]) -> list[str]:
    """Require a non-empty string `id` on a nested item and reject one already
    used earlier in the SAME list. `seen` is mutated with each accepted id.

    A missing id is normally repaired upstream by `normalise_nested_ids`; a
    duplicate is the model reusing one id for two items, which survives every
    other check here and then collides on `key={...}` in the learner renderer.
    """
    errs = _require_str(where, item, "id")
    if errs:
        return errs
    item_id = cast(str, item.get("id"))
    if item_id in seen:
        return [f"{where} duplicate id {item_id!r}"]
    seen.add(item_id)
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
    card_ids: set[str] = set()
    for j, card in enumerate(cards):
        cwhere = f"{where}.cards[{j}]"
        if not isinstance(card, dict):
            errs.append(f"{cwhere} must be an object")
            continue
        card_fields = cast(Mapping[str, object], card)
        errs += _require_unique_id(cwhere, card_fields, card_ids)
        errs += _require_str(cwhere, card_fields, "title")
        errs += _require_str(cwhere, card_fields, "body")
    return errs


def _validate_quiz(where: str, block: Mapping[str, object]) -> list[str]:
    questions = block.get("questions")
    if not isinstance(questions, list) or not questions:
        return [f"{where}.questions must be a non-empty list"]
    errs: list[str] = []
    question_ids: set[str] = set()
    for j, question in enumerate(questions):
        qwhere = f"{where}.questions[{j}]"
        if not isinstance(question, dict):
            errs.append(f"{qwhere} must be an object")
            continue
        question_fields = cast(Mapping[str, object], question)
        errs += _require_unique_id(qwhere, question_fields, question_ids)
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
    step_ids: set[str] = set()
    for j, step in enumerate(steps):
        swhere = f"{where}.steps[{j}]"
        if not isinstance(step, dict):
            errs.append(f"{swhere} must be an object")
            continue
        step_fields = cast(Mapping[str, object], step)
        errs += _require_unique_id(swhere, step_fields, step_ids)
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
            # bucket_ids doubles as the set the items below are cross-checked
            # against; a duplicate id is reported but stays in the set, so a
            # dangling-bucketId error is never raised on top of it.
            errs += _require_unique_id(bwhere, bucket_fields, bucket_ids)
            errs += _require_str(bwhere, bucket_fields, "label")
    items = block.get("items")
    item_ids: set[str] = set()
    if not isinstance(items, list):
        errs.append(f"{where}.items must be a list")
    else:
        for j, item in enumerate(items):
            iwhere = f"{where}.items[{j}]"
            if not isinstance(item, dict):
                errs.append(f"{iwhere} must be an object")
                continue
            item_fields = cast(Mapping[str, object], item)
            errs += _require_unique_id(iwhere, item_fields, item_ids)
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
            # Like the sort buckets above, option_ids is also the set
            # correctOptionId is resolved against.
            errs += _require_unique_id(owhere, option_fields, option_ids)
            errs += _require_str(owhere, option_fields, "label")
            errs += _require_str(owhere, option_fields, "reason")
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
    candidate_ids: set[str] = set()
    for j, candidate in enumerate(candidates):
        cwhere = f"{where}.candidates[{j}]"
        if not isinstance(candidate, dict):
            errs.append(f"{cwhere} must be an object")
            continue
        candidate_fields = cast(Mapping[str, object], candidate)
        errs += _require_unique_id(cwhere, candidate_fields, candidate_ids)
        errs += _require_str(cwhere, candidate_fields, "text")
        errs += _require_str(cwhere, candidate_fields, "reason")
        if not isinstance(candidate.get("isFlaw"), bool):
            errs.append(f"{cwhere}.isFlaw must be a bool")
    return errs


def normalise_nested_ids(blocks: object) -> list[Any]:
    """Mint a deterministic `id` for every nested item that has none, returning
    a NEW array. Never mutates its input (same discipline as
    services/media_blocks.py).

    WHY this exists: the real catalogue predates the nested-id rule. Measured
    over db/baseline/data/lessons.json, 66 of 91 lessons carry at least one
    id-less nested item — 214 of 328 cards and 202 of 282 quiz questions have
    no `id` (every TOP-level block id is present). The content-improvement
    agent is told to copy unchanged blocks through verbatim, so on those
    lessons a faithful copy would fail `validate_content_blocks` forever: the
    draft is thrown away, its source feedback is marked covered, and the
    admin's only recovery re-queues the lesson to burn another 16k-token call
    and fail identically. Normalising repairs the draft instead, and approving
    it back-fills the ids into the stored lesson — the gap heals one lesson at
    a time rather than blocking the feature.

    Scheme: `f"{block_id}-{list_name}{index}"` — `"b3-cards0"`,
    `"b3-questions1"`. Deterministic (two runs over the same block produce the
    same ids) and unique within the block, since `(list_name, index)` is. In
    the rare case the derived id collides with one the block already carries,
    `-1`, `-2`, … is appended until it is free.

    Only the nested lists this module validates are walked. Non-list input
    returns an empty list; non-dict entries pass through untouched — including
    a quiz question's `options`, which is a list of plain STRINGS and stays
    strings. A block with no usable `id` of its own is passed through
    untouched: there is nothing stable to derive from, and inventing a parent
    id here would hide a defect `validate_content_blocks` should report.
    """
    if not isinstance(blocks, list):
        return []
    result: list[Any] = []
    for block in blocks:
        if not isinstance(block, dict):
            result.append(block)
            continue
        block_id = block.get("id")
        if not isinstance(block_id, str) or not block_id:
            result.append(block)
            continue
        result.append(_normalise_block(cast("dict[str, Any]", block), block_id))
    return result


def _normalise_block(block: dict[str, Any], block_id: str) -> dict[str, Any]:
    """A copy of `block` with ids minted into its nested lists, or `block`
    itself when nothing was missing."""
    patched: dict[str, Any] = {}
    for name in _NESTED_ID_LISTS:
        entries = block.get(name)
        if not isinstance(entries, list):
            continue
        replacement = _normalise_entries(cast("list[Any]", entries), block_id, name)
        if replacement is not None:
            patched[name] = replacement
    return {**block, **patched} if patched else block


def _usable_id(entry: object) -> str | None:
    """The entry's own `id` if it is a dict carrying a non-empty string one."""
    if not isinstance(entry, dict):
        return None
    entry_id = entry.get("id")
    return entry_id if isinstance(entry_id, str) and entry_id else None


def _normalise_entries(entries: list[Any], block_id: str, name: str) -> list[Any] | None:
    """A copy of `entries` with an id minted into every id-less dict entry, or
    None when every entry already had one (so the block can be left alone)."""
    taken = {found for entry in entries if (found := _usable_id(entry)) is not None}
    result: list[Any] = []
    minted_any = False
    for index, entry in enumerate(entries):
        # Non-dict entries (a quiz question's plain-string options) and entries
        # that already have an id are carried across as they are.
        if not isinstance(entry, dict) or _usable_id(entry) is not None:
            result.append(entry)
            continue
        minted = _free_id(f"{block_id}-{name}{index}", taken)
        taken.add(minted)
        result.append({**cast("dict[str, Any]", entry), "id": minted})
        minted_any = True
    return result if minted_any else None


def _free_id(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    suffix = 1
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


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


# --- house style (backend/prompts/house_style.md, rules marked [enforced]) ---

# The house style's own top-level scalar text fields, by block type. `quiz`
# and `card_group` are absent here — their prose lives inside `questions` /
# `cards`, walked separately below (see _QUIZ_TEXT_FIELDS and _LIST_TEXT_FIELDS).
# `image` deliberately excludes `alt`: that is accessibility text, not learner
# -facing prose voice, so an em dash or "Artifact" there is not a house-style
# problem. It stays covered by validate_content_blocks's non-empty-string
# requirement — nothing is lost, only judged by the right rule.
_SCALAR_TEXT_FIELDS: dict[str, tuple[str, ...]] = {
    "heading": ("text",),
    "paragraph": ("text",),
    "callout": ("text",),
    "kicker": ("text",),
    "question": ("prompt",),
    "try_it_yourself": ("task", "material", "whatToNotice"),
    "interactive": ("prompt", "example"),
    "image": ("caption",),
    "video": ("caption",),
}
# The nested-list text fields this module already knows how to walk (same
# lists as _NESTED_ID_LISTS), keyed to the field names on each entry that
# carry prose. `questions`' own `q`/`explanation` plus its `options` (a list of
# plain strings, not dicts) are handled separately by _quiz_text_fields.
_LIST_TEXT_FIELDS: dict[str, tuple[str, ...]] = {
    "cards": ("title", "body"),
    "steps": ("label", "text"),
    "buckets": ("label",),
    "items": ("text", "reason"),
    "options": ("label", "reason"),  # interactive predict-mode options (dicts)
    "candidates": ("text", "reason"),
}

_FORBIDDEN_CHARS = "—–…"  # em dash, en dash, ellipsis
_ARTIFACT_RE = re.compile(r"\bartifacts?\b", re.IGNORECASE)  # singular AND plural
_BOLD_SPAN_RE = re.compile(r"\*\*(.+?)\*\*")
# A bullet lead-in is `- **Term.**` at the very start of a line: a bold span
# whose content ends in a period, opening right after "- ". Only bold spans of
# exactly this shape are exempt from the two-span cap.
_BULLET_LEAD_IN_RE = re.compile(r"(?m)^-[ \t]\*\*[^*\n]+\.\*\*")
_CHECK_UNDERSTANDING_HEADING = "Check your understanding"


def check_house_style(base: object, proposed: object) -> list[str]:
    """Enforce the **[enforced]** rules from backend/prompts/house_style.md
    against the blocks the agent actually WROTE. Returns human-readable error
    strings; empty means the proposal is clean.

    Matches proposed blocks to base blocks by id, exactly like
    `check_media_immutable` above, and only judges a block that is new (no
    base counterpart) or whose content differs from its base counterpart (a
    direct dict comparison — the JSON-equivalent of that block). A block
    copied through unchanged is exempt.

    This scoping is load-bearing, not an optimisation. The real lesson corpus
    predates these rules (see `normalise_nested_ids`'s docstring for the same
    story with nested ids): applying them to every block, changed or not,
    rejects a faithful copy of ordinary legacy content, and the calling
    service records that as a `failed` proposal — the exact failure mode a
    validator tightening produced in this feature's own review, where it
    turned out to reject 66 of 91 real lessons. Scoping to changed blocks
    makes the agent accountable for its own writing and nothing else.

    Rule 6 (a quiz needs a "Check your understanding" heading immediately
    before it) is the one exception to "only the quiz's own dict matters":
    that invariant belongs to the (heading, quiz) PAIR, i.e. to the quiz's
    ADJACENCY, not to its own content. It is evaluated whenever the quiz
    itself changed, OR its immediate-predecessor identity differs between
    `base` and `proposed` (a different block now sits there, including "no
    block at all" when the quiz has been moved to the very front), OR that
    predecessor is the same block in both but its own content changed (e.g.
    the heading text was edited in place). A quiz whose predecessor is the
    same block, unchanged, in both arrays is exempt regardless of what that
    predecessor is — that is what keeps a legacy quiz that never had the
    heading, and never gets touched, out of the gate. An index shift caused
    by something inserted earlier in the array is NOT an adjacency change and
    does not trip this on its own.

    Callers are expected to also run `validate_content_blocks` and
    `check_media_immutable` — this function only carries the house-style
    rules, not structural or media-locator validation.
    """
    if not isinstance(proposed, list):
        return ["proposed content_blocks must be a list"]
    base_by_id = _blocks_by_id(base)
    base_list = base if isinstance(base, list) else []
    base_index_by_id = _index_by_id(base_list)
    errors: list[str] = []
    for i, block in enumerate(proposed):
        if not isinstance(block, dict):
            continue
        block = cast(dict[str, Any], block)
        changed = _is_changed(block, base_by_id)
        where = f"block[{i}]"
        if changed:
            for path, text in _text_fields(where, block):
                errors.extend(_check_text_field(path, text))
            if block.get("type") == "quiz":
                errors.extend(_check_quiz_correctness(where, block))
        if block.get("type") == "quiz" and _quiz_heading_rule_applies(
            i, block, changed, proposed, base_list, base_by_id, base_index_by_id
        ):
            errors.extend(_check_quiz_heading(where, proposed, i))
    return errors


def _index_by_id(blocks: list[Any]) -> dict[str, int]:
    """Every block's position within `blocks`, keyed by id — used to find what
    preceded a given (now possibly moved) block in the BASE array."""
    index_by_id: dict[str, int] = {}
    for idx, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        block_id = block.get("id")
        if isinstance(block_id, str) and block_id:
            index_by_id[block_id] = idx
    return index_by_id


# A sentinel distinct from every possible string id, representing "this block
# has no predecessor" (it is at index 0). Needed so a quiz moved to the very
# front of the array is recognised as an adjacency change rather than quietly
# treated as "no predecessor either way, so nothing changed" — the exact gap
# a pure `base = [heading, quiz]` / `proposed = [quiz, heading]` reorder
# exposed.
_NO_PREDECESSOR = object()


def _predecessor_id(blocks: list[Any], index: int) -> object:
    """The id of `blocks[index - 1]`, or `_NO_PREDECESSOR` when there is no
    such block (index is 0), it isn't a dict, or it has no usable string id."""
    if index <= 0:
        return _NO_PREDECESSOR
    prev = blocks[index - 1]
    if isinstance(prev, dict):
        prev_id = prev.get("id")
        if isinstance(prev_id, str) and prev_id:
            return prev_id
    return _NO_PREDECESSOR


def _quiz_heading_rule_applies(
    index: int,
    quiz: Mapping[str, object],
    quiz_changed: bool,
    proposed: list[Any],
    base_list: list[Any],
    base_by_id: dict[str, dict[str, Any]],
    base_index_by_id: dict[str, int],
) -> bool:
    """True when this proposal could have broken the quiz's adjacency to its
    required heading: the quiz itself changed, its predecessor identity
    differs between `base` and `proposed`, or its predecessor is the same
    block in both but was itself edited."""
    if quiz_changed:
        return True
    quiz_id = quiz.get("id")
    base_index = base_index_by_id.get(quiz_id) if isinstance(quiz_id, str) else None
    base_pred_id = (
        _predecessor_id(base_list, base_index) if base_index is not None else _NO_PREDECESSOR
    )
    proposed_pred_id = _predecessor_id(proposed, index)
    if base_pred_id != proposed_pred_id:
        return True
    proposed_prev = proposed[index - 1] if index > 0 else None
    return isinstance(proposed_prev, dict) and _is_changed(
        cast(dict[str, Any], proposed_prev), base_by_id
    )


def _check_quiz_heading(where: str, proposed: list[Any], index: int) -> list[str]:
    """Rule 6 alone: the block immediately before `proposed[index]` (the
    quiz) must be a heading reading exactly "Check your understanding"."""
    preceding = proposed[index - 1] if index > 0 else None
    if _is_check_understanding_heading(preceding):
        return []
    return [
        f"{where} must be immediately preceded by a heading reading "
        f"{_CHECK_UNDERSTANDING_HEADING!r}"
    ]


def _blocks_by_id(blocks: object) -> dict[str, dict[str, Any]]:
    """The base's blocks keyed by id, for matching a proposal's blocks back to
    their base counterpart. Skips non-list input, non-dict entries, and blocks
    with no non-empty string id (nothing to match them by)."""
    by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(blocks, list):
        return by_id
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_id = block.get("id")
        if isinstance(block_id, str) and block_id:
            by_id[block_id] = cast(dict[str, Any], block)
    return by_id


def _is_changed(block: dict[str, Any], base_by_id: dict[str, dict[str, Any]]) -> bool:
    """True when `block` is new (no base counterpart to match by id) or its
    content differs from that counterpart. A block with no id of its own
    cannot be matched to a base block at all, so it is treated as changed —
    the agent produced it, whether or not it is well-formed."""
    block_id = block.get("id")
    if not isinstance(block_id, str) or not block_id:
        return True
    return base_by_id.get(block_id) != block


def _text_fields(where: str, block: dict[str, Any]) -> list[tuple[str, str]]:
    """Every text-bearing (path, text) pair on one changed block, walking the
    same nested lists `validate_content_blocks` knows about. Non-string or
    empty values are skipped; there is nothing to check in them."""
    btype = block.get("type")
    fields: list[tuple[str, str]] = []
    for name in _SCALAR_TEXT_FIELDS.get(btype, ()):
        _add_scalar(fields, where, block, name)
    if btype == "quiz":
        fields.extend(_quiz_text_fields(where, block))
    else:
        for list_name, item_fields in _LIST_TEXT_FIELDS.items():
            fields.extend(_list_text_fields(where, block, list_name, item_fields))
    return fields


def _add_scalar(
    fields: list[tuple[str, str]], where: str, block: Mapping[str, object], name: str
) -> None:
    value = block.get(name)
    if isinstance(value, str) and value:
        fields.append((f"{where}.{name}", value))


def _list_text_fields(
    where: str, block: Mapping[str, object], list_name: str, item_fields: tuple[str, ...]
) -> list[tuple[str, str]]:
    entries = block.get(list_name)
    if not isinstance(entries, list):
        return []
    fields: list[tuple[str, str]] = []
    for j, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        ewhere = f"{where}.{list_name}[{j}]"
        for name in item_fields:
            _add_scalar(fields, ewhere, cast(Mapping[str, object], entry), name)
    return fields


def _quiz_text_fields(where: str, block: Mapping[str, object]) -> list[tuple[str, str]]:
    """A quiz's prose lives inside `questions`, one level deeper than every
    other block type's nested lists: each question carries `q`, `explanation`,
    and `options` — a list of plain strings, not dicts."""
    questions = block.get("questions")
    if not isinstance(questions, list):
        return []
    fields: list[tuple[str, str]] = []
    for j, question in enumerate(questions):
        if not isinstance(question, dict):
            continue
        qwhere = f"{where}.questions[{j}]"
        _add_scalar(fields, qwhere, cast(Mapping[str, object], question), "q")
        _add_scalar(fields, qwhere, cast(Mapping[str, object], question), "explanation")
        options = question.get("options")
        if isinstance(options, list):
            for k, option in enumerate(options):
                if isinstance(option, str) and option:
                    fields.append((f"{qwhere}.options[{k}]", option))
    return fields


def _check_text_field(path: str, text: str) -> list[str]:
    """Rules 1-3: no forbidden dash/ellipsis, at most two bold spans (bullet
    lead-ins exempt), and never the word "Artifact"."""
    errors: list[str] = []
    if any(ch in text for ch in _FORBIDDEN_CHARS):
        errors.append(f"{path} contains a forbidden dash or ellipsis")
    if _has_too_many_bold_spans(text):
        errors.append(f"{path} has more than two bold spans")
    if _ARTIFACT_RE.search(text):
        errors.append(f"{path} uses 'Artifact'; house style requires 'Artefact'")
    return errors


def _has_too_many_bold_spans(text: str) -> bool:
    """The cap is on bold spans OTHER than bullet lead-ins, not on the total.
    A field can carry any number of `- **Term.**` lead-ins (house_style.md
    models exactly that pattern) plus up to two ordinary bold spans — exempt
    the lead-ins first, then cap what remains."""
    bullet_spans = _bullet_lead_in_bold_spans(text)
    non_exempt = [m.span() for m in _BOLD_SPAN_RE.finditer(text) if m.span() not in bullet_spans]
    return len(non_exempt) > 2


def _bullet_lead_in_bold_spans(text: str) -> set[tuple[int, int]]:
    """The (start, end) span of the `**...**` inside every `- **Term.**`
    bullet lead-in at the start of a line, so `_has_too_many_bold_spans` can
    filter these out of the count before applying the two-span cap."""
    spans: set[tuple[int, int]] = set()
    for match in _BULLET_LEAD_IN_RE.finditer(text):
        bold_start = match.group().index("**") + match.start()
        spans.add((bold_start, match.end()))
    return spans


def _check_quiz_correctness(where: str, block: Mapping[str, object]) -> list[str]:
    """Rules 4-5, both specific to a changed `quiz` block's own questions: the
    correct answer is never the unique longest option, and (when there is more
    than one question) the `correct` index is not identical across every one
    of them. Rule 6 (the preceding heading) lives in `_check_quiz_heading` —
    it applies under broader conditions than "this block changed", see
    `_quiz_heading_rule_applies`."""
    errors: list[str] = []
    questions = block.get("questions")
    if isinstance(questions, list):
        corrects: list[int] = []
        for j, question in enumerate(questions):
            if not isinstance(question, dict):
                continue
            correct = question.get("correct")
            if isinstance(correct, int) and not isinstance(correct, bool):
                corrects.append(correct)
                errors.extend(
                    _check_longest_option(
                        f"{where}.questions[{j}]",
                        cast(Mapping[str, object], question),
                        correct,
                    )
                )
        if len(questions) > 1 and len(corrects) == len(questions) and len(set(corrects)) == 1:
            errors.append(f"{where}.questions 'correct' index is identical across every question")
    return errors


def _check_longest_option(qwhere: str, question: Mapping[str, object], correct: int) -> list[str]:
    options = question.get("options")
    if not isinstance(options, list) or not options or not all(isinstance(o, str) for o in options):
        return []
    if not 0 <= correct < len(options):
        return []
    lengths = [len(cast(str, o)) for o in options]
    longest = max(lengths)
    if lengths[correct] == longest and lengths.count(longest) == 1:
        return [f"{qwhere}.correct is the unique longest option"]
    return []


def _is_check_understanding_heading(block: object) -> bool:
    if not isinstance(block, dict) or block.get("type") != "heading":
        return False
    text = block.get("text")
    return isinstance(text, str) and text.strip() == _CHECK_UNDERSTANDING_HEADING
