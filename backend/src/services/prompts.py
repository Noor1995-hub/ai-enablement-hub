from __future__ import annotations

from pathlib import Path

__all__ = ["load_prompt", "read_file", "set_cache", "reset_cache", "clear_cache"]

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_CACHE: dict[str, str] = {}


def read_file(kind: str) -> str:
    """The shipped default for `kind` (ignores overrides)."""
    return (_PROMPTS_DIR / f"{kind}.md").read_text(encoding="utf-8").strip()


def load_prompt(kind: str) -> str:
    """Active prompt: an admin DB override once primed into the cache (see
    PromptService.refresh_cache — lifespan startup + every save/reset), else the file."""
    cached = _CACHE.get(kind)
    if cached is not None:
        return cached
    text = read_file(kind)
    _CACHE[kind] = text
    return text


def set_cache(kind: str, content: str) -> None:
    _CACHE[kind] = content


def reset_cache(kind: str) -> None:
    _CACHE.pop(kind, None)


def clear_cache() -> None:
    _CACHE.clear()
