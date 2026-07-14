from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from src.schemas.feedback import FeedbackCreate


def test_strips_and_accepts_message() -> None:
    model = FeedbackCreate(lesson_id=uuid.uuid4(), message="  needs an example  ")
    assert model.message == "needs an example"


def test_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        FeedbackCreate(lesson_id=uuid.uuid4(), message="")


def test_rejects_whitespace_only_message() -> None:
    with pytest.raises(ValidationError):
        FeedbackCreate(lesson_id=uuid.uuid4(), message="   \n\t ")


def test_rejects_oversized_message() -> None:
    with pytest.raises(ValidationError):
        FeedbackCreate(lesson_id=uuid.uuid4(), message="x" * 4001)
