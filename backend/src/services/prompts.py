from __future__ import annotations

from functools import lru_cache
from pathlib import Path

__all__ = ["load_prompt"]

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache
def load_prompt(kind: str) -> str:
    """Reads backend/prompts/<kind>.md. All 4 kinds ship a file in this batch
    (placeholders for 3, real minimal content for chatbot) — a missing file is
    an internal mistake, not a case to handle gracefully."""
    return (_PROMPTS_DIR / f"{kind}.md").read_text(encoding="utf-8").strip()
