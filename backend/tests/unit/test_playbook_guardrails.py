"""Code-enforced playbook rules (#149). The prompt says never invent a system; the learner's
playbook screen shows each use case's systems, so code drops any system the person never
named, in their interview answers or their assessment."""

from __future__ import annotations

import copy
from typing import Any

from src.services.playbook_guardrails import drop_unnamed_systems
from tests.fixtures.playbook import EXTRACTION

_SOURCES = [
    "I keep everything in Excel and send it round by Outlook.",
    "Tools used: Microsoft 365 Copilot, ChatGPT",
    "The paper checklists live in a binder.",
]


def _with_systems(*systems: list[str]) -> dict[str, Any]:
    data = copy.deepcopy(EXTRACTION)
    use_cases = data["shared"]["use_cases"]
    for use_case, names in zip(use_cases, systems, strict=False):
        use_case["systems_involved"] = names
    return data


def _systems(data: dict[str, Any]) -> list[list[str]]:
    return [uc["systems_involved"] for uc in data["shared"]["use_cases"]]


def test_systems_the_person_named_are_kept() -> None:
    data = _with_systems(["Excel", "outlook"], ["Microsoft 365 Copilot"])

    result, dropped = drop_unnamed_systems(data, _SOURCES)

    assert _systems(result) == [["Excel", "outlook"], ["Microsoft 365 Copilot"]]
    assert dropped == 0


def test_a_system_never_named_is_dropped() -> None:
    data = _with_systems(["Excel", "Site-level tracking sheets"], ["Smartphone voice-recorder"])

    result, dropped = drop_unnamed_systems(data, _SOURCES)

    assert _systems(result) == [["Excel"], []]
    assert dropped == 2


def test_a_bracketed_note_and_a_vendor_prefix_do_not_count_against_a_name() -> None:
    data = _with_systems(["Excel (source notes)", "Microsoft Excel"], ["Microsoft Outlook"])

    result, _dropped = drop_unnamed_systems(data, _SOURCES)

    assert _systems(result) == [["Excel (source notes)", "Microsoft Excel"], ["Microsoft Outlook"]]


def test_a_plural_of_a_longer_name_still_matches() -> None:
    data = _with_systems(["Paper checklist"], [])

    result, _dropped = drop_unnamed_systems(data, _SOURCES)

    assert _systems(result) == [["Paper checklist"], []]


def test_a_short_name_must_match_exactly() -> None:
    # "SAP" must not match inside another word, and "Teams" is not "team".
    sources = ["Our team saps the energy out of the close."]
    data = _with_systems(["SAP", "Teams"], [])

    result, dropped = drop_unnamed_systems(data, sources)

    assert _systems(result) == [[], []]
    assert dropped == 2


def test_a_combined_name_is_kept_only_if_every_part_was_named() -> None:
    data = _with_systems(["Spreadsheet / Excel"], ["Excel / Outlook"])

    result, dropped = drop_unnamed_systems(data, _SOURCES)

    assert _systems(result) == [[], ["Excel / Outlook"]]
    assert dropped == 1


def test_the_input_is_not_changed_and_internal_is_untouched() -> None:
    data = _with_systems(["Invented Tool"], [])
    before = copy.deepcopy(data)

    result, _dropped = drop_unnamed_systems(data, _SOURCES)

    assert data == before
    assert result["internal"] == before["internal"]


def test_a_name_that_starts_or_ends_with_a_symbol_still_matches() -> None:
    # PR #162 review: \b never matches next to a symbol at the edge of a name.
    sources = ["We write C# services, some C++ and a .NET API."]
    data = _with_systems(["C#", "C++"], [".NET"])

    result, dropped = drop_unnamed_systems(data, sources)

    assert _systems(result) == [["C#", "C++"], [".NET"]]
    assert dropped == 0
