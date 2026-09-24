from __future__ import annotations

from pathlib import Path

__all__ = ["load_prompt", "read_file", "clear_cache"]

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
