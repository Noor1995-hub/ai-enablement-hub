from src.services.interview_marker import READY_MARKER, has_ready_marker, strip_ready_marker


def test_strip_removes_marker_and_trailing_whitespace() -> None:
    assert strip_ready_marker(f"Want me to build it?\n{READY_MARKER}") == "Want me to build it?"


def test_strip_leaves_text_without_marker_untouched() -> None:
    assert strip_ready_marker("Plain turn.  ") == "Plain turn.  "


def test_has_ready_marker() -> None:
    assert has_ready_marker(f"x\n{READY_MARKER}") is True
    assert has_ready_marker("x") is False
