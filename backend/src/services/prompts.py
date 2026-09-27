from __future__ import annotations

import hashlib
from pathlib import Path

__all__ = ["load_prompt", "prompt_version", "read_file", "clear_cache"]

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_CACHE: dict[str, str] = {}


def read_file(kind: str) -> str:
    """The shipped prompt for `kind` — `backend/prompts/<kind>.md`."""
    return (_PROMPTS_DIR / f"{kind}.md").read_text(encoding="utf-8").strip()


def load_prompt(kind: str) -> str:
    """The active prompt. Git is the only source of truth (2026-09-23): this is always the
    shipped file, read once per process and cached."""
    cached = _CACHE.get(kind)
    if cached is not None:
        return cached
    text = read_file(kind)
    _CACHE[kind] = text
    return text


def clear_cache() -> None:
    _CACHE.clear()
    _VERSION_CACHE.clear()


_VERSION_CACHE: dict[str, str] = {}


def prompt_version(kind: str) -> str:
    """Which version of the prompt is active: the first 12 hex chars of the SHA-256 of the
    shipped text. Git is the prompt history (2026-09-23), so a stamped run maps back to a
    commit by hashing `backend/prompts/<kind>.md` at that commit. Cached like the text itself
    (it runs on every chat turn)."""
    cached = _VERSION_CACHE.get(kind)
    if cached is not None:
        return cached
    version = hashlib.sha256(load_prompt(kind).encode("utf-8")).hexdigest()[:12]
    _VERSION_CACHE[kind] = version
    return version
