"""Golden-parity suite for the scoring port (design-backend.md §5).

Replays tests/golden/scoring_golden.json — generated from the REAL legacy
scoring.js by generate_scoring_golden.mjs — against the Python port. Exact
equality on every field (including mandatory_modules ordering) and on every
422 status + message.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.services.scoring import ScoringError, score_response

_GOLDEN = Path(__file__).resolve().parent.parent / "golden" / "scoring_golden.json"


def _load_cases() -> list[dict[str, Any]]:
    cases = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert len(cases) > 500, "golden corpus looks truncated"
    return cases


_CASES = _load_cases()


@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_golden_parity(case: dict[str, Any]) -> None:
    if "error" in case:
        with pytest.raises(ScoringError) as excinfo:
            score_response(case["input"])
        assert excinfo.value.status == case["error"]["status"]
        assert excinfo.value.message == case["error"]["message"]
    else:
        assert score_response(case["input"]) == case["expected"]


def test_corpus_covers_the_null_c5_trap() -> None:
    """Guard the corpus itself: the JS `null >= 2` trap must stay exercised."""
    null_c5 = [c for c in _CASES if "expected" in c and c["expected"]["c5_rung"] is None]
    assert len(null_c5) >= 5
    trap = next(c for c in _CASES if c["name"] == "no_use-null-c5-otherwise-integrator")
    assert trap["expected"]["score_level"] == "practitioner"
    assert trap["expected"]["mandatory_modules"] == []


def test_corpus_covers_all_levels_and_errors() -> None:
    levels = {c["expected"]["score_level"] for c in _CASES if "expected" in c}
    assert levels == {"explore", "practitioner", "integrator"}
    assert any("error" in c for c in _CASES)
    ordered = next(c for c in _CASES if c["name"] == "mandatory-both-ordered")
    assert ordered["expected"]["mandatory_modules"] == ["safe-use", "trust"]
