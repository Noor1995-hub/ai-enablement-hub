# backend/tests/unit/test_org_service.py
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractOrgRepository
from src.services.exceptions import DuplicateCompanyNameError, NotFoundError
from src.services.org_service import OrgService


async def test_resolve_ai_settings_defaults_all_four_to_false() -> None:
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_ai_settings.return_value = []
    service = OrgService(org)

    settings = await service.resolve_ai_settings(uuid.uuid4())

    assert settings == {"chatbot": False, "assessment": False, "lesson": False, "interview": False}


async def test_resolve_ai_settings_none_project_id_is_all_false() -> None:
    org = AsyncMock(spec=AbstractOrgRepository)
    service = OrgService(org)

    settings = await service.resolve_ai_settings(None)

    assert settings == {"chatbot": False, "assessment": False, "lesson": False, "interview": False}
    org.get_ai_settings.assert_not_awaited()


async def test_resolve_ai_settings_reflects_stored_rows() -> None:
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_ai_settings.return_value = [SimpleNamespace(kind="chatbot", enabled=True)]
    service = OrgService(org)

    settings = await service.resolve_ai_settings(uuid.uuid4())

    assert settings["chatbot"] is True
    assert settings["lesson"] is False


async def test_set_ai_surface_unknown_project_raises_not_found() -> None:
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_project.return_value = None
    service = OrgService(org)

    with pytest.raises(NotFoundError):
        await service.set_ai_surface(uuid.uuid4(), "chatbot", enabled=True)


async def test_rename_company_refuses_a_name_another_company_has() -> None:
    org = AsyncMock(spec=AbstractOrgRepository)
    me, other = SimpleNamespace(id=uuid.uuid4()), SimpleNamespace(id=uuid.uuid4())
    org.get_company.return_value = me
    org.get_company_by_name_ci.return_value = other
    with pytest.raises(DuplicateCompanyNameError):
        await OrgService(org).rename_company(me.id, "Beta")
    org.rename_company.assert_not_awaited()


async def test_rename_company_to_its_own_name_in_another_case_is_fine() -> None:
    org = AsyncMock(spec=AbstractOrgRepository)
    me = SimpleNamespace(id=uuid.uuid4())
    org.get_company.return_value = me
    org.get_company_by_name_ci.return_value = me
    await OrgService(org).rename_company(me.id, "  ACME ")
    org.rename_company.assert_awaited_once_with(me, "ACME")


async def test_rename_unknown_company_or_project_is_404() -> None:
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_company.return_value = None
    org.get_project.return_value = None
    with pytest.raises(NotFoundError):
        await OrgService(org).rename_company(uuid.uuid4(), "x")
    with pytest.raises(NotFoundError):
        await OrgService(org).rename_project(uuid.uuid4(), "x")
