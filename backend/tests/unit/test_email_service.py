"""EmailService + templates: ACS message shape, both-path invite content,
HTML escaping, failure swallowing, and the provider's feature-flag branches."""

from __future__ import annotations

from pydantic import SecretStr

from src.core.configs.auth import AuthSettings
from src.core.configs.settings import Settings
from src.core.dependencies.email import get_email_service
from src.services.email_service import EmailSender, EmailService
from tests.fixtures.email import TEST_EMAIL, RaisingSender, RecordingSender

APP_URL = "http://testserver:5173"
INVITE_LINK = f"{APP_URL}/invite/tok-123_abc"


def _service(sender: EmailSender, *, entra_enabled: bool = True) -> EmailService:
    return EmailService(
        sender,
        sender_address=TEST_EMAIL.sender_address,
        app_url=APP_URL,
        entra_enabled=entra_enabled,
        invite_ttl_days=7,
        reset_ttl_days=1,
    )


class TestInviteEmail:
    async def test_message_shape_and_both_sign_in_paths(self) -> None:
        sender = RecordingSender()
        ok = await _service(sender).send_invite_email(
            to="sarah@example.com", first_name="Sarah", invite_link=INVITE_LINK
        )
        assert ok is True
        [message] = sender.messages
        assert message["senderAddress"] == TEST_EMAIL.sender_address
        assert message["recipients"] == {"to": [{"address": "sarah@example.com"}]}
        content = message["content"]
        assert "invited" in content["subject"].lower()
        for body in (content["plainText"], content["html"]):
            assert INVITE_LINK in body
            # The Microsoft path goes to the login page, never the OIDC endpoint.
            assert f"{APP_URL}/login" in body
            assert "/api/auth/entra" not in body
        assert "7 days" in content["plainText"]

    async def test_entra_off_hides_the_microsoft_path(self) -> None:
        sender = RecordingSender()
        await _service(sender, entra_enabled=False).send_invite_email(
            to="sarah@example.com", first_name="Sarah", invite_link=INVITE_LINK
        )
        [message] = sender.messages
        for body in (message["content"]["plainText"], message["content"]["html"]):
            assert INVITE_LINK in body
            assert f"{APP_URL}/login" not in body
            assert "Microsoft" not in body

    async def test_html_escapes_admin_entered_name(self) -> None:
        sender = RecordingSender()
        await _service(sender).send_invite_email(
            to="ob@example.com", first_name="O'Brien & <co>", invite_link=INVITE_LINK
        )
        [message] = sender.messages
        assert "O'Brien & <co>" in message["content"]["plainText"]
        assert "O&#x27;Brien &amp; &lt;co&gt;" in message["content"]["html"]
        assert "<co>" not in message["content"]["html"]

    async def test_send_failure_returns_false(self) -> None:
        ok = await _service(RaisingSender()).send_invite_email(
            to="sarah@example.com", first_name="Sarah", invite_link=INVITE_LINK
        )
        assert ok is False


class TestResetEmail:
    async def test_message_shape_and_singular_ttl(self) -> None:
        sender = RecordingSender()
        ok = await _service(sender).send_reset_email(
            to="resettee@example.com", first_name="Res", reset_link=INVITE_LINK
        )
        assert ok is True
        [message] = sender.messages
        assert message["recipients"] == {"to": [{"address": "resettee@example.com"}]}
        content = message["content"]
        assert "reset" in content["subject"].lower()
        for body in (content["plainText"], content["html"]):
            assert INVITE_LINK in body
        assert "1 day" in content["plainText"]
        assert "1 days" not in content["plainText"]

    async def test_send_failure_returns_false(self) -> None:
        ok = await _service(RaisingSender()).send_reset_email(
            to="resettee@example.com", first_name="Res", reset_link=INVITE_LINK
        )
        assert ok is False


class TestProvider:
    _AUTH = AuthSettings(jwt_secret=SecretStr("unit-test-jwt-secret-0123456789abc"))

    def test_unconfigured_returns_none(self) -> None:
        settings = Settings(auth=self._AUTH, email=None)
        assert get_email_service(settings) is None

    def test_configured_builds_service(self) -> None:
        # from_connection_string only parses — no I/O happens here.
        settings = Settings(auth=self._AUTH, email=TEST_EMAIL)
        service = get_email_service(settings)
        assert isinstance(service, EmailService)
