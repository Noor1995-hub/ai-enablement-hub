"""pyproject.toml invariants: every dependency is bounded and declared once."""

from __future__ import annotations

import tomllib
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _project() -> dict:
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]


def _unbounded(deps: list[str]) -> list[str]:
    return [d for d in deps if "~=" not in d and "==" not in d and "<" not in d]


def _name(dep: str) -> str:
    for sep in ("~=", "==", ">=", "<", "["):
        dep = dep.split(sep)[0]
    return dep.strip().lower()


def test_every_main_dependency_has_an_upper_bound() -> None:
    assert _unbounded(_project()["dependencies"]) == []


def test_every_optional_dependency_has_an_upper_bound() -> None:
    groups = _project()["optional-dependencies"].values()
    assert _unbounded([d for group in groups for d in group]) == []


def test_anthropic_is_a_main_dependency() -> None:
    assert any(_name(d) == "anthropic" for d in _project()["dependencies"])


def test_no_dependency_is_declared_twice() -> None:
    project = _project()
    names = [_name(d) for d in project["dependencies"]]
    for group in project["optional-dependencies"].values():
        names.extend(_name(d) for d in group)
    assert {n for n in names if names.count(n) > 1} == set()
