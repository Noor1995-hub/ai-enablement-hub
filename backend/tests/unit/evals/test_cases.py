from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.interviewer import cases


def _write(path: Path, case_id: str, status: str) -> None:
    path.write_text(json.dumps({"id": case_id, "status": status}), encoding="utf-8")


def test_list_and_load_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cases, "CASES_DIR", tmp_path)
    _write(tmp_path / "a.json", "a", "approved")

    assert cases.list_case_ids() == ["a"]
    assert cases.load_case("a")["status"] == "approved"


def test_write_case_round_trips_through_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cases, "CASES_DIR", tmp_path)

    cases.write_case({"id": "b", "status": "draft"})

    assert cases.load_case("b") == {"id": "b", "status": "draft"}


def test_approved_cases_with_explicit_ids_raises_on_a_draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cases, "CASES_DIR", tmp_path)
    _write(tmp_path / "a.json", "a", "draft")

    with pytest.raises(SystemExit, match="not approved"):
        cases.approved_cases(["a"])


def test_approved_cases_with_no_ids_silently_skips_drafts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cases, "CASES_DIR", tmp_path)
    _write(tmp_path / "a.json", "a", "draft")
    _write(tmp_path / "b.json", "b", "approved")

    result = cases.approved_cases(None)

    assert [c["id"] for c in result] == ["b"]
