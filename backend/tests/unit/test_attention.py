from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.core.attention import attention_for

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)


def _base(**overrides):
    kwargs = {
        "now": NOW,
        "created_at": NOW - timedelta(days=30),
        "activated": True,
        "activated_known_since": NOW - timedelta(days=30),
        "has_survey": True,
        "latest_completion": NOW - timedelta(days=1),
        "assigned_total": 10,
        "completed_total": 3,
        "track_names_in_progress": ["Copilot"],
    }
    kwargs.update(overrides)
    return kwargs


def test_healthy_learner_is_none() -> None:
    assert attention_for(**_base()) is None


def test_never_activated_after_nudge_window() -> None:
    kind, reason = attention_for(**_base(activated=False, has_survey=False))
    assert kind == "never_activated"


def test_fresh_invite_not_flagged() -> None:
    assert (
        attention_for(
            **_base(activated=False, has_survey=False, created_at=NOW - timedelta(days=2))
        )
        is None
    )


def test_not_assessed() -> None:
    kind, reason = attention_for(
        **_base(has_survey=False, latest_completion=None, assigned_total=0, completed_total=0)
    )
    assert kind == "not_assessed"
    assert "assessment not started" in reason


def test_stalled_with_track_name() -> None:
    kind, reason = attention_for(**_base(latest_completion=NOW - timedelta(days=16)))
    assert kind == "stalled"
    assert "Copilot" in reason and "16 days" in reason


def test_completed_everything_never_stalls() -> None:
    assert (
        attention_for(**_base(completed_total=10, latest_completion=NOW - timedelta(days=60)))
        is None
    )
