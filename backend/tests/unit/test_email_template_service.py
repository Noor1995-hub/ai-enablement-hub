"""EmailTemplateService: per-project resolution with code-default fallback,
save-time validation, and rendering for the send + preview paths."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.repositories.base import AbstractEmailTemplateRepository, AbstractOrgRepository
from src.services.email_template_service import EmailTemplateService
from src.services.email_templates import DEFAULT_TEMPLATES
from src.services.exceptions import InvalidEmailTemplateError, NotFoundError

PROJECT_ID = uuid.uuid4()
LINK = "http://testserver:5173/invite/tok_ABC"


def _service(
    *,
    project: object | None = SimpleNamespace(id=PROJECT_ID, name="Acme"),
    row: object | None = None,
) -> tuple[EmailTemplateService, AsyncMock, AsyncMock]:
    templates = AsyncMock(spec=AbstractEmailTemplateRepository)
    templates.get.return_value = row
    templates.list_for_project.return_value = [row] if row is not None else []
    org = AsyncMock(spec=AbstractOrgRepository)
    org.get_project.return_value = project
    return EmailTemplateService(templates, org), templates, org


class TestResolve:
    async def test_falls_back_to_default_when_no_override(self) -> None:
        service, _, _ = _service(row=None)
        resolved = await service.resolve(PROJECT_ID, "invite")
        assert resolved.subject == DEFAULT_TEMPLATES["invite"].subject
        assert resolved.is_custom is False

    async def test_returns_the_override_when_present(self) -> None:
        row = SimpleNamespace(purpose="invite", subject="Custom", body_markdown="{{invite_link}}")
        service, _, _ = _service(row=row)
        resolved = await service.resolve(PROJECT_ID, "invite")
        assert resolved.subject == "Custom"
        assert resolved.is_custom is True

    async def test_none_project_resolves_to_default(self) -> None:
        service, templates, _ = _service(row=None)
        resolved = await service.resolve(None, "reset")
        assert resolved.is_custom is False
        templates.get.assert_not_awaited()


class TestGetTemplates:
    async def test_unknown_project_is_404(self) -> None:
        service, _, _ = _service(project=None)
        with pytest.raises(NotFoundError):
            await service.get_templates(PROJECT_ID)

    async def test_returns_both_purposes_mixing_custom_and_default(self) -> None:
        row = SimpleNamespace(purpose="invite", subject="Custom", body_markdown="{{invite_link}}")
        service, _, _ = _service(row=row)
        by_purpose = {t.purpose: t for t in await service.get_templates(PROJECT_ID)}
        assert set(by_purpose) == {"invite", "reset"}
        assert by_purpose["invite"].is_custom is True
        assert by_purpose["reset"].is_custom is False


class TestSetAndClear:
    async def test_set_validates_before_upsert(self) -> None:
        service, templates, _ = _service()
        with pytest.raises(InvalidEmailTemplateError):
            await service.set_template(PROJECT_ID, "invite", "Hi", "no link token here")
        templates.upsert.assert_not_awaited()

    async def test_set_upserts_a_valid_template(self) -> None:
        service, templates, _ = _service()
        await service.set_template(PROJECT_ID, "invite", "Hi", "Welcome\n\n{{invite_link}}")
        templates.upsert.assert_awaited_once_with(
            PROJECT_ID, "invite", subject="Hi", body_markdown="Welcome\n\n{{invite_link}}"
        )

    async def test_set_unknown_project_is_404(self) -> None:
        service, templates, _ = _service(project=None)
        with pytest.raises(NotFoundError):
            await service.set_template(PROJECT_ID, "invite", "Hi", "{{invite_link}}")
        templates.upsert.assert_not_awaited()

    async def test_clear_deletes_the_override(self) -> None:
        service, templates, _ = _service()
        await service.clear_template(PROJECT_ID, "invite")
        templates.delete.assert_awaited_once_with(PROJECT_ID, "invite")


class TestRender:
    async def test_render_uses_resolved_template_and_injects_project_name(self) -> None:
        service, _, _ = _service(row=None)
        content = await service.render(
            PROJECT_ID,
            "invite",
            first_name="Sarah",
            last_name="Jones",
            link=LINK,
            ttl_days=7,
            login_url="http://x/login",
        )
        assert "Sarah" in content.plain_text
        assert LINK in content.plain_text
        assert LINK in content.html

    async def test_render_with_no_project_uses_default_and_blank_project_name(self) -> None:
        service, _, org = _service()
        content = await service.render(
            None, "reset", first_name="Res", last_name="Et", link=LINK, ttl_days=1
        )
        assert LINK in content.plain_text
        org.get_project.assert_not_awaited()


class TestPreview:
    async def test_preview_renders_the_supplied_unsaved_template(self) -> None:
        service, templates, _ = _service()
        content = await service.preview(
            PROJECT_ID,
            "invite",
            subject="Draft {{first_name}}",
            body_markdown="Hi {{first_name}} from {{project_name}}\n\n{{invite_link}}",
            app_url="http://testserver:5173",
            ttl_days=7,
        )
        assert "Draft Alex" in content.subject
        assert "Acme" in content.html
        assert 'href="http://testserver:5173/invite/example-invite-token"' in content.html
        # Preview never persists.
        templates.upsert.assert_not_awaited()

    async def test_preview_unknown_project_is_404(self) -> None:
        service, _, _ = _service(project=None)
        with pytest.raises(NotFoundError):
            await service.preview(
                PROJECT_ID,
                "invite",
                subject="s",
                body_markdown="{{invite_link}}",
                app_url="http://x",
                ttl_days=7,
            )
