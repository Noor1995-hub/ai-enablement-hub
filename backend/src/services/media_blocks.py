"""Pure content_blocks transforms for lesson media (no I/O; style precedent:
email_templates.py). `url` on image/uploaded-video blocks is ephemeral (a
freshly-stamped SAS at read time) and must never be persisted; `url` on
embed-video blocks is author-entered and must never be touched by either
helper. Both functions tolerate unknown/malformed entries by passing them
through untouched, and never mutate their input."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["stamp_urls", "strip_ephemeral"]


def _is_ephemeral_url_block(block: dict[str, Any]) -> bool:
    block_type = block.get("type")
    if block_type == "image":
        return True
    return block_type == "video" and block.get("source") == "blob"


def strip_ephemeral(blocks: list[Any]) -> list[Any]:
    """Drop `url` from image blocks and blob-sourced video blocks (called
    before persisting a lesson write); embed-video `url` and anything else
    passes through untouched."""
    result: list[Any] = []
    for block in blocks:
        if isinstance(block, dict) and _is_ephemeral_url_block(block) and "url" in block:
            block = {key: value for key, value in block.items() if key != "url"}
        result.append(block)
    return result


def stamp_urls(blocks: list[Any], url_for: Callable[[str], str]) -> list[Any]:
    """Set a fresh `url` on a copy of every image/blob-video block that has a
    non-empty `blob_path` (called at read time); embed videos, blocks without
    a `blob_path`, and unknown/malformed entries pass through untouched."""
    result: list[Any] = []
    for block in blocks:
        if isinstance(block, dict) and _is_ephemeral_url_block(block) and block.get("blob_path"):
            block = {**block, "url": url_for(block["blob_path"])}
        result.append(block)
    return result
