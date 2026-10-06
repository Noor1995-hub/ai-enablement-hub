"""Valid media blob paths (B6). Uploads are named `<kind>s/<uuid4 hex><ext>`
(services/media_service.py), so the library only ever touches that shape —
anything else (traversal, other prefixes) is rejected before storage sees it."""

from __future__ import annotations

import re

__all__ = ["media_path"]

_KINDS = frozenset({"images", "videos"})
_NAME = re.compile(r"^[0-9a-f]{32}\.[a-z0-9]{2,5}$")


def media_path(kind: str, name: str) -> str | None:
    if kind not in _KINDS or not _NAME.fullmatch(name):
        return None
    return f"{kind}/{name}"
