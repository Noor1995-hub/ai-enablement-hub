from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.schemas.feedback import FeedbackCreate, FeedbackResponse


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


def test_accepts_message_at_limit_after_stripping() -> None:
    # Raw length 4002, stripped length exactly 4000 — must be accepted, stored stripped.
    model = FeedbackCreate(lesson_id=uuid.uuid4(), message=" " + "a" * 4000 + " ")
    assert model.message == "a" * 4000


def test_rejects_message_over_limit_after_stripping() -> None:
    with pytest.raises(ValidationError):
        FeedbackCreate(lesson_id=uuid.uuid4(), message="a" * 4001)


def test_response_validates_from_orm_attributes() -> None:
    row = SimpleNamespace(id=uuid.uuid4(), created_at=datetime(2026, 7, 14, 12, 0, 0))
    response = FeedbackResponse.model_validate(row)
    assert response.id == row.id
    assert response.created_at == row.created_at
