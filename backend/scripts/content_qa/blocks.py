"""Walk the prose out of a lessons.content_blocks list."""

from __future__ import annotations

from collections.abc import Iterator

# Keys whose string values are identifiers/config, not learner-facing prose.
NON_PROSE_KEYS = frozenset(
    {
        "id",
        "type",
        "mode",
        "source",
        "size",
        "level",
        "blob_path",
        "url",
        "bucketId",
        "correctOptionId",
    }
)


def iter_texts(blocks: list[dict]) -> Iterator[tuple[str, str]]:
    """Yield (path, text) for every prose string across a content_blocks list."""
    for i, block in enumerate(blocks or []):
        yield from _walk(block, f"blocks[{i}]")


def _walk(node: object, path: str) -> Iterator[tuple[str, str]]:
    if isinstance(node, str):
        if node.strip():
            yield (path, node)
    elif isinstance(node, dict):
        for key, value in node.items():
            if key in NON_PROSE_KEYS:
                continue
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            yield from _walk(item, f"{path}[{idx}]")
