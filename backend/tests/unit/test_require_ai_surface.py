# backend/tests/unit/test_require_ai_surface.py
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.core.dependencies.chat import require_ai_surface
from src.services.org_service import OrgService


async def test_raises_403_when_disabled() -> None:
    org = AsyncMock(spec=OrgService)
    org.resolve_ai_settings.return_value = {
        "chatbot": False,
        "assessment": False,
        "lesson": False,
        "interview": False,
    }
    user = type("U", (), {"project_id": uuid.uuid4()})()

    with pytest.raises(HTTPException) as exc_info:
        await require_ai_surface(kind="chatbot", user=user, org=org)  # ty: ignore[invalid-argument-type]
    assert exc_info.value.status_code == 403


async def test_raises_403_when_no_project() -> None:
    org = AsyncMock(spec=OrgService)
    user = type("U", (), {"project_id": None})()

    with pytest.raises(HTTPException) as exc_info:
        await require_ai_surface(kind="chatbot", user=user, org=org)  # ty: ignore[invalid-argument-type]
    assert exc_info.value.status_code == 403
    org.resolve_ai_settings.assert_not_awaited()


async def test_passes_when_enabled() -> None:
    org = AsyncMock(spec=OrgService)
    org.resolve_ai_settings.return_value = {
        "chatbot": True,
        "assessment": False,
        "lesson": False,
        "interview": False,
    }
    user = type("U", (), {"project_id": uuid.uuid4()})()

    await require_ai_surface(
        kind="chatbot",
        user=user,  # ty: ignore[invalid-argument-type]
        org=org,
    )  # does not raise
