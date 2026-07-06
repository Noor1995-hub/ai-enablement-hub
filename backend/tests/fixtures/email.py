"""Email test doubles: EmailSettings for tests plus recording/raising
stand-ins for the ACS EmailClient's begin_send."""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from src.core.configs.email import EmailSettings

__all__ = ["TEST_EMAIL", "RaisingSender", "RecordingSender"]

# The accesskey only has to parse (base64); from_connection_string does no I/O.
TEST_EMAIL = EmailSettings(
    connection_string=SecretStr(
        "endpoint=https://unit.test.communication.azure.com/;accesskey=dGVzdC1rZXk="
    ),
    sender_address="DoNotReply@test.azurecomm.net",
)


class RecordingSender:
    """Captures every message begin_send receives; the send succeeds."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def begin_send(self, message: Any) -> Any:
        self.messages.append(message)
        return None


class RaisingSender:
    """Every send blows up (dead ACS endpoint, bad credentials, ...)."""

    def begin_send(self, message: Any) -> Any:
        msg = "ACS unreachable"
        raise RuntimeError(msg)
