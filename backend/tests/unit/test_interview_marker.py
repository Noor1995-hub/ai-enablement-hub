from src.services.interview_marker import READY_MARKER, has_ready_marker, strip_ready_marker


def test_strip_removes_marker_and_trailing_whitespace() -> None:
    assert strip_ready_marker(f"Want me to build it?\n{READY_MARKER}") == "Want me to build it?"


def test_strip_leaves_text_without_marker_untouched() -> None:
    assert strip_ready_marker("Plain turn.  ") == "Plain turn.  "


def test_has_ready_marker() -> None:
    assert has_ready_marker(f"x\n{READY_MARKER}") is True
    assert has_ready_marker("x") is False


def test_strip_removes_a_leading_marker_and_its_line_break() -> None:
    # #96: the marker now opens the offer turn, so the stop at "?\n\n" cannot cut it off.
    assert strip_ready_marker(f"{READY_MARKER}\nThat's plenty. Shall I build it?") == (
        "That's plenty. Shall I build it?"
    )


def test_strip_leaves_no_stray_space_where_the_marker_sat_mid_turn() -> None:
    # Seen in the v5 eval: the model sometimes writes the marker inline, "[[...]] With that".
    text = f"Clear picture, thanks.\n\n{READY_MARKER} With that, shall I build it?"
    assert strip_ready_marker(text) == "Clear picture, thanks.\n\nWith that, shall I build it?"
