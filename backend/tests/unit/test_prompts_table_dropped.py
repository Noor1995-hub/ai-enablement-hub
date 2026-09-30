"""The `prompts` table was retired in PR #16 and dropped by migration e5f6a7b8c9d0."""

from __future__ import annotations

import src.db.models as models
from src.db.base import Base


def test_prompts_table_and_model_are_gone() -> None:
    assert "prompts" not in Base.metadata.tables
    assert not hasattr(models, "Prompt")
