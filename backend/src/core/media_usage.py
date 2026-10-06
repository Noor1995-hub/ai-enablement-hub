"""Which media blobs a content_blocks array references (B6 media library).
Pure and shape-tolerant: lessons and AI proposals are opaque JSONB."""

from __future__ import annotations

from typing import Any

__all__ = ["blob_paths"]


def blob_paths(blocks: Any) -> set[str]:
    """Image blob_paths and stored-video blob_paths (source == "blob"). Embed
    videos point outside our storage; empty paths are upload placeholders."""
    found: set[str] = set()
    if not isinstance(blocks, list):
        return found
    for block in blocks:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        path = block.get("blob_path")
        if not isinstance(path, str) or not path:
            continue
        if kind == "image" or (kind == "video" and block.get("source") == "blob"):
            found.add(path)
    return found
