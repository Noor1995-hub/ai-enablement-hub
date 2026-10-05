"""The interview playbook as a tagged document (#149).

The model used to write the playbook as JSON inside a tool call: about 7,000 tokens of prose in
which every quote must be escaped. One slip (a quoted phrase, a stray brace) broke the whole
box, about one attempt in five. Now the model writes plain text in tags named after the schema
fields, and this module turns that document into the same PlaybookExtraction dict. Prose inside
a tag is taken literally, so quotes, braces and line breaks need no escaping.

The pydantic schema is the single source of truth: the template the prompt shows, the renderer
and the parser all walk the same fields. Fields code can know are derived, not asked for:
a use case's rank and start_here, and a next move's order, come from position."""

from __future__ import annotations

import re
import types
from dataclasses import dataclass, field
from typing import Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel

from src.schemas.interview import NextMove, PlaybookExtraction, UseCase

__all__ = [
    "PlaybookFormatError",
    "output_template",
    "parse_playbook",
    "render_playbook_document",
]

_ITEM = "item"
_YES = ("yes", "true", "ja")
_NO = ("no", "false", "nee")


def _derived(model: type[BaseModel], position: int) -> dict[str, Any]:
    """Fields code fills from the item's position in its list."""
    if model is UseCase:
        return {"rank": position + 1, "start_here": position == 0}
    if model is NextMove:
        return {"order": position + 1}
    return {}


_DERIVED_FIELDS: dict[type[BaseModel], frozenset[str]] = {
    UseCase: frozenset({"rank", "start_here"}),
    NextMove: frozenset({"order"}),
}


class PlaybookFormatError(Exception):
    """The document does not match the template. `problems` name tag paths only, never the
    text (it comes from the learner's interview)."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


# --- schema walking -----------------------------------------------------------------------


def _fields(model: type[BaseModel]) -> list[tuple[str, Any]]:
    skip = _DERIVED_FIELDS.get(model, frozenset())
    return [
        (name, info.annotation) for name, info in model.model_fields.items() if name not in skip
    ]


def _is_model(annotation: Any) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def _list_item_type(annotation: Any) -> Any | None:
    return get_args(annotation)[0] if get_origin(annotation) is list else None


def _is_optional(annotation: Any) -> bool:
    return get_origin(annotation) in (Union, types.UnionType) and type(None) in get_args(annotation)


def _all_tags() -> set[str]:
    tags = {"internal", "shared", _ITEM}

    def walk(model: type[BaseModel]) -> None:
        for name, annotation in _fields(model):
            tags.add(name)
            inner = _list_item_type(annotation) or annotation
            if _is_model(inner):
                walk(inner)

    walk(PlaybookExtraction)
    return tags


def _text_tags() -> frozenset[str]:
    """Field names that hold text (or a yes/no, number or fixed value) wherever they appear:
    such a field can't contain tags, so the next tag ends it even without its closing tag."""
    kinds: dict[str, set[bool]] = {}

    def walk(model: type[BaseModel]) -> None:
        for name, annotation in _fields(model):
            item_type = _list_item_type(annotation)
            kinds.setdefault(name, set()).add(item_type is None and not _is_model(annotation))
            inner = item_type or annotation
            if _is_model(inner):
                walk(inner)

    walk(PlaybookExtraction)
    return frozenset(name for name, is_text in kinds.items() if is_text == {True})


_TAG_RE = re.compile(r"<(/?)(" + "|".join(sorted(_all_tags(), key=len, reverse=True)) + r")>")
_TEXT_TAGS = _text_tags()


# --- rendering ------------------------------------------------------------------------------


def render_playbook_document(data: dict[str, Any]) -> str:
    """A PlaybookExtraction dict as the tagged document the model is asked to write."""
    lines: list[str] = []
    _render_model(PlaybookExtraction, data, lines)
    return "\n".join(lines) + "\n"


def _render_model(model: type[BaseModel], data: dict[str, Any], lines: list[str]) -> None:
    for name, annotation in _fields(model):
        _render_value(name, annotation, data[name], lines)


def _render_value(tag: str, annotation: Any, value: Any, lines: list[str]) -> None:
    item_type = _list_item_type(annotation)
    if _is_model(annotation):
        lines.append(f"<{tag}>")
        _render_model(annotation, value, lines)
        lines.append(f"</{tag}>")
    elif item_type is not None:
        lines.append(f"<{tag}>")
        for item in value:
            _render_value(_ITEM, item_type, item, lines)
        lines.append(f"</{tag}>")
    elif isinstance(value, bool):
        lines.append(f"<{tag}>{'yes' if value else 'no'}</{tag}>")
    else:
        lines.append(f"<{tag}>{'' if value is None else value}</{tag}>")


def output_template() -> str:
    """The template shown in the prompt: every tag, in order, with a hint for its value."""
    lines: list[str] = []
    _template_model(PlaybookExtraction, lines)
    return "\n".join(lines)


def _template_model(model: type[BaseModel], lines: list[str]) -> None:
    for name, annotation in _fields(model):
        _template_value(name, annotation, lines)


def _template_value(tag: str, annotation: Any, lines: list[str]) -> None:
    item_type = _list_item_type(annotation)
    if _is_model(annotation):
        lines.append(f"<{tag}>")
        _template_model(annotation, lines)
        lines.append(f"</{tag}>")
    elif item_type is not None:
        lines.append(f"<{tag}>")
        item_hint, list_note = _LIST_HINTS.get(
            tag, ("", f"(repeat the {_ITEM} block for each entry; none if there are none)")
        )
        if item_hint:
            lines.append(f"<{_ITEM}>{item_hint}</{_ITEM}>")
        else:
            _template_value(_ITEM, item_type, lines)
        # No tag tokens in the note: a copied note line must not open a tag.
        lines.append(list_note)
        lines.append(f"</{tag}>")
    else:
        lines.append(f"<{tag}>{_hint(annotation)}</{tag}>")


# Lists whose example item would invite the model to fill them in anyway: a specific hint for
# the item, and a note that an empty list is fine (#149, v13: invented systems).
_LIST_HINTS: dict[str, tuple[str, str]] = {
    "systems_involved": (
        "a system the person named",
        "(one item per system the person named; no items if they named none)",
    ),
}


def _hint(annotation: Any) -> str:
    if annotation is bool:
        return "yes or no"
    if annotation is int:
        return "a number"
    if get_origin(annotation) is Literal:
        return "one of: " + ", ".join(str(v) for v in get_args(annotation))
    if _is_optional(annotation):
        return "text, or leave empty"
    return "text"


# --- parsing --------------------------------------------------------------------------------


@dataclass
class _Node:
    tag: str
    start: int
    end: int = -1
    children: list[_Node] = field(default_factory=list)


def parse_playbook(text: str) -> dict[str, Any]:
    """The tagged document as a PlaybookExtraction dict, with the derived fields filled in.
    Raises PlaybookFormatError naming every structural problem found. Values are not checked
    beyond yes/no and numbers: pydantic validates the result."""
    problems: list[str] = []
    root = _build_tree(text, problems)
    if problems:
        raise PlaybookFormatError(problems)
    value = _parse_model(root, PlaybookExtraction, text, "", 0, problems)
    if problems:
        raise PlaybookFormatError(problems)
    return value


def _build_tree(text: str, problems: list[str]) -> _Node:
    root = _Node(tag="", start=0)
    stack = [root]
    for match in _TAG_RE.finditer(text):
        closing, tag = match.group(1) == "/", match.group(2)
        if stack[-1].tag in _TEXT_TAGS and not (closing and tag == stack[-1].tag):
            # A text field left open ends at the next tag: it can't contain one.
            stack[-1].end = match.start()
            stack.pop()
        if not closing:
            node = _Node(tag=tag, start=match.end())
            stack[-1].children.append(node)
            stack.append(node)
            continue
        if stack[-1].tag == tag:
            stack[-1].end = match.start()
            stack.pop()
        elif any(n.tag == tag for n in stack[1:]):
            # Something inside was left open: report the innermost one.
            problems.append(f"{_path(stack)}: not closed")
            return root
        # A closing tag with nothing open is stray: ignore it, like other text.
    if len(stack) > 1:
        problems.append(f"{_path(stack)}: not closed")
    return root


def _path(stack: list[_Node]) -> str:
    return ".".join(n.tag for n in stack[1:])


def _parse_model(
    node: _Node,
    model: type[BaseModel],
    text: str,
    path: str,
    position: int,
    problems: list[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, annotation in _fields(model):
        where = f"{path}.{name}" if path else name
        matches = [c for c in node.children if c.tag == name]
        if not matches:
            problems.append(f"{where}: missing")
            continue
        if len(matches) > 1:
            if _list_item_type(annotation) is None:
                problems.append(f"{where}: duplicated")
                continue
            # A list written in two blocks is one list, its items in order.
            first = matches[0]
            matches = [
                _Node(
                    tag=name,
                    start=first.start,
                    end=first.end,
                    children=[child for m in matches for child in m.children],
                )
            ]
        result[name] = _parse_value(matches[0], annotation, text, where, problems)
    result.update(_derived(model, position))
    # Keep the schema's field order, so a parsed playbook equals a stored one key for key.
    order = list(model.model_fields)
    return {k: result[k] for k in sorted(result, key=order.index)}


def _parse_value(node: _Node, annotation: Any, text: str, path: str, problems: list[str]) -> Any:
    item_type = _list_item_type(annotation)
    if _is_model(annotation):
        return _parse_model(node, annotation, text, path, 0, problems)
    if item_type is not None:
        items = [c for c in node.children if c.tag == _ITEM]
        if _is_model(item_type):
            return [
                _parse_model(item, item_type, text, f"{path}.{i}", i, problems)
                for i, item in enumerate(items)
            ]
        return [_inner(item, text) for item in items]
    value = _inner(node, text)
    if annotation is bool:
        lowered = value.lower().rstrip(".").strip()
        if lowered in _YES:
            return True
        if lowered in _NO:
            return False
        problems.append(f"{path}: not yes or no")
        return None
    if annotation is int:
        try:
            return int(value.rstrip(".").strip())
        except ValueError:
            problems.append(f"{path}: not a number")
            return None
    if _is_optional(annotation) and not value:
        return None
    if get_origin(annotation) is Literal:
        # A fixed value in other capitals is the fixed value. Anything else is left for
        # pydantic to reject.
        for allowed in get_args(annotation):
            if str(allowed).casefold() == value.casefold():
                return allowed
    return value


def _inner(node: _Node, text: str) -> str:
    """The text between a tag's open and close, outer whitespace stripped. Line breaks inside
    stay: the summary's bullets are one per line."""
    return text[node.start : node.end].strip()
