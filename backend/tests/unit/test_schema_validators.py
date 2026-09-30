"""The shared blank-string field validator. Three schema modules copy-defined
this before it lived in one place (review 9.4a / prior audit 4.6)."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from src.schemas._validators import require_non_blank
from src.schemas.admin_content import LessonUpdateRequest, TrackCreateRequest
from src.schemas.admin_org import CompanyCreateRequest
from src.schemas.admin_users import InviteRequest


class TestRequireNonBlank:
    def test_passes_a_real_value(self) -> None:
        assert require_non_blank("Copilot") == "Copilot"

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="must not be blank"):
            require_non_blank("   ")

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="must not be blank"):
            require_non_blank("")

    def test_allows_none(self) -> None:
        """Optional fields on the Update schemas pass None through — omitting a
        field is not the same as blanking it."""
        assert require_non_blank(None) is None

    def test_does_not_strip(self) -> None:
        """Validation only; the services own trimming (content_service.py
        `.strip()`s on write), so this must not silently change stored values."""
        assert require_non_blank("  Copilot  ") == "  Copilot  "


class TestWiredIntoTheSchemas:
    """Behaviour parity guards: each of the three modules must still reject a
    blank on the fields it validated before the hoist."""

    def test_track_name_blank_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TrackCreateRequest(name="  ", track_type="general", color=None)

    def test_lesson_title_blank_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LessonUpdateRequest(title="  ")

    def test_lesson_title_omitted_is_allowed(self) -> None:
        assert LessonUpdateRequest().title is None

    def test_company_name_blank_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CompanyCreateRequest(name=" ")

    def test_invite_names_blank_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            InviteRequest(
                email="x@example.com", first_name=" ", last_name="Y", project_id=uuid.uuid4()
            )
