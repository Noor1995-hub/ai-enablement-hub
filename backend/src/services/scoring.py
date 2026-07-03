"""Pure port of the legacy survey scorer (app/api/_lib/scoring.js).

Zero I/O and zero framework imports on purpose: parity with the legacy scorer
is proven by replaying tests/golden/scoring_golden.json (generated from the
real scoring.js) through :func:`score_response`.

Every deviation risk between the two languages is handled explicitly; the big
one is the c5 rung: it is ``None`` when the learner selected NO_USE alone, and
JS ``null >= 2`` is ``false`` while Python ``None >= 2`` raises ``TypeError`` —
hence the ``is not None`` guards in the integrator gate and mandatory modules.
"""

from __future__ import annotations

from typing import Any

__all__ = ["ScoringError", "score_response"]

RUNG = {"MISSING": 0, "PARTIAL": 1, "HAVE": 2, "ADV_D": 3, "ADV_E": 3}

USAGE_BAND_MATRIX: dict[str, dict[str, str]] = {
    "NEVER": {
        "NONE": "dormant",
        "FEW": "dormant",
        "SEVERAL": "dormant",
        "MOST": "dormant",
        "ALL": "dormant",
    },
    "MONTHLY": {
        "NONE": "dormant",
        "FEW": "occasional",
        "SEVERAL": "occasional",
        "MOST": "occasional",
        "ALL": "regular",
    },
    "WEEKLY": {
        "NONE": "occasional",
        "FEW": "occasional",
        "SEVERAL": "regular",
        "MOST": "regular",
        "ALL": "regular",
    },
    "DAILY": {
        "NONE": "occasional",
        "FEW": "regular",
        "SEVERAL": "regular",
        "MOST": "embedded",
        "ALL": "embedded",
    },
    "INTENSIVE": {
        "NONE": "occasional",
        "FEW": "regular",
        "SEVERAL": "embedded",
        "MOST": "embedded",
        "ALL": "embedded",
    },
}


class ScoringError(Exception):
    """A required answer code is missing or unrecognised (HTTP 422)."""

    status = 422

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _competency_rung(code: Any, bucket: str) -> int:
    if code is None:
        raise ScoringError(f"Missing answer for {bucket}")
    rung = RUNG.get(code) if isinstance(code, str) else None
    if rung is None:
        raise ScoringError(f'Unrecognised code "{code}" for {bucket}')
    return rung


def _c5_rung(codes: Any) -> tuple[int | None, bool]:
    """Ordered first-match cascade; rung None means N/A (NO_USE alone)."""
    if not isinstance(codes, list) or len(codes) == 0:
        raise ScoringError("C5 requires at least one selection")

    pub = "PUBLIC_PASTE" in codes
    app = "APPROVED_PASTE" in codes
    kept = "KEPT_OUT" in codes
    unsure = "UNSURE" in codes
    no_use = "NO_USE" in codes

    safety_flag = pub
    rung: int | None
    if pub:
        rung = 1 if (app or kept) else 0
    elif app:  # noqa: SIM114 — branches kept separate to mirror the JS cascade 1:1
        rung = 2
    elif kept:
        rung = 2
    elif unsure:
        rung = 1
    elif no_use and len(codes) == 1:
        rung = None  # N/A — not demonstrated
    else:
        raise ScoringError("C5: unrecognised combination")

    return rung, safety_flag


def _usage_band(freq: Any, breadth: Any) -> str | None:
    row = USAGE_BAND_MATRIX.get(freq) if isinstance(freq, str) else None
    if row is None or not isinstance(breadth, str):
        return None
    return row.get(breadth)


def score_response(answers: dict[str, Any]) -> dict[str, Any]:
    """Score a completed survey; returns every field written to survey_responses.

    Raises :class:`ScoringError` (→ HTTP 422) when a required answer code is
    missing or unrecognised. Evaluation order matches the legacy scorer exactly
    (c1..c4, then c6, then c5) so the first error reported is identical.
    """
    c1_rung = _competency_rung(answers.get("c1_code"), "c1")
    c2_rung = _competency_rung(answers.get("c2_code"), "c2")
    c3_rung = _competency_rung(answers.get("c3_code"), "c3")
    c4_rung = _competency_rung(answers.get("c4_code"), "c4")
    c6_rung = _competency_rung(answers.get("c6_code"), "c6")
    c5_rung, safety_flag = _c5_rung(answers.get("c5_codes"))

    # Band counts — capability buckets only (#1–#4).
    cap_rungs = [c1_rung, c2_rung, c3_rung, c4_rung]
    have_count = sum(1 for rung in cap_rungs if rung >= 2)
    adv_count = sum(1 for rung in cap_rungs if rung == 3)

    # Level (Multiplier excluded for now). JS `null >= 2` is false: a None c5
    # never satisfies the integrator gate.
    c5_ok = c5_rung is not None and c5_rung >= 2
    if have_count == 4 and adv_count >= 2 and c5_ok and c6_rung >= 2:
        score_level = "integrator"
    elif have_count >= 3:
        score_level = "practitioner"
    else:
        score_level = "explore"

    mandatory_modules = []
    if c5_rung is not None and c5_rung < 2:
        mandatory_modules.append("safe-use")
    if c6_rung < 2:
        mandatory_modules.append("trust")

    return {
        "score_level": score_level,
        "c1_rung": c1_rung,
        "c2_rung": c2_rung,
        "c3_rung": c3_rung,
        "c4_rung": c4_rung,
        "c5_rung": c5_rung,
        "c6_rung": c6_rung,
        "have_count": have_count,
        "adv_count": adv_count,
        "safety_flag": safety_flag,
        "mandatory_modules": mandatory_modules,
        "usage_band": _usage_band(answers.get("b_freq"), answers.get("b_breadth")),
    }
