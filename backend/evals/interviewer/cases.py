"""cases/<id>.json read/write (spec §3.2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ["CASES_DIR", "approved_cases", "list_case_ids", "load_case", "write_case"]

CASES_DIR = Path(__file__).resolve().parent / "cases"


def list_case_ids() -> list[str]:
    return sorted(p.stem for p in CASES_DIR.glob("*.json"))


def load_case(case_id: str) -> dict[str, Any]:
    return json.loads((CASES_DIR / f"{case_id}.json").read_text(encoding="utf-8"))


def write_case(case: dict[str, Any]) -> None:
    path = CASES_DIR / f"{case['id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def approved_cases(case_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Explicit ids (`run --cases a,b`) must already be approved, or this refuses loudly.
    `None` (`run` over everything) silently uses whichever cases on disk are approved -
    a case still in review just is not part of the run yet."""
    if case_ids is not None:
        loaded = [load_case(i) for i in case_ids]
        not_approved = [c["id"] for c in loaded if c["status"] != "approved"]
        if not_approved:
            raise SystemExit(f"not approved yet: {', '.join(not_approved)}")
        return loaded
    return [c for c in (load_case(i) for i in list_case_ids()) if c["status"] == "approved"]
