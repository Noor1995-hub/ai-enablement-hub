from __future__ import annotations

from src.services.calibration_prompt import (
    MAX_INJECTED_CHARS,
    MAX_INJECTED_NOTES,
    render_calibration_block,
)


def test_no_notes_renders_nothing() -> None:
    # "" is the signal for the caller to skip the section entirely rather than
    # inject a header with nothing under it.
    assert render_calibration_block([]) == ""


def test_notes_are_numbered_in_the_order_given() -> None:
    block = render_calibration_block(["first note", "second note"])

    assert "1. first note" in block
    assert "2. second note" in block
    assert block.index("first note") < block.index("second note")


def test_the_header_says_the_notes_are_not_enforced() -> None:
    block = render_calibration_block(["a note"])

    lowered = block.lower()
    assert "not" in lowered and "enforced" in lowered


def test_the_note_count_is_capped() -> None:
    block = render_calibration_block([f"note {i}" for i in range(20)], max_notes=3)

    assert "note 2" in block
    assert "note 3" not in block


def test_the_character_budget_drops_from_the_end() -> None:
    notes = ["x" * 200, "y" * 200, "z" * 200]

    block = render_calibration_block(notes, max_chars=len(render_calibration_block(notes[:2])))

    assert "y" * 200 in block
    assert "z" * 200 not in block


def test_one_oversized_note_is_still_kept() -> None:
    # Dropping everything would silently lose a legitimate long note.
    block = render_calibration_block(["q" * 5000], max_chars=100)

    assert "q" * 5000 in block


def test_the_defaults_are_the_documented_bounds() -> None:
    assert MAX_INJECTED_NOTES == 8
    assert MAX_INJECTED_CHARS == 1500
