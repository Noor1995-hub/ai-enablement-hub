"""EmailService (ACS transport): message shape, failure swallowing, and the
provider's feature-flag branches. Content/template behavior lives in
test_email_templates.py / test_email_template_service.py."""

from __future__ import annotations

from pydantic import SecretStr

from src.core.configs.auth import AuthSettings
from src.core.configs.settings import Settings
from src.core.dependencies.email import get_email_service
from src.services.email_service import EmailSender, EmailService
from src.services.email_templates import EmailContent
from tests.fixtures.email import TEST_EMAIL, RaisingSender, RecordingSender

CONTENT = EmailContent(
    subject="Hello",
    plain_text="plain body http://x/invite/tok",
    html="<html><body>html body</body></html>",
)


def _service(sender: EmailSender) -> EmailService:
    return EmailService(sender, sender_address=TEST_EMAIL.sender_address)


class TestSend:
    async def test_builds_the_acs_message_and_reports_accepted(self) -> None:
        sender = RecordingSender()
        ok = await _service(sender).send("sarah@example.com", CONTENT)
        assert ok is True
        [message] = sender.messages
        assert message["senderAddress"] == TEST_EMAIL.sender_address
        assert message["recipients"] == {"to": [{"address": "sarah@example.com"}]}
        assert message["content"] == {
            "subject": "Hello",
            "plainText": CONTENT.plain_text,
            "html": CONTENT.html,
        }

    async def test_send_failure_returns_false(self) -> None:
        ok = await _service(RaisingSender()).send("sarah@example.com", CONTENT)
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
