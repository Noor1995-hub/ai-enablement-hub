from __future__ import annotations

import logging
from typing import Any, Protocol

from starlette.concurrency import run_in_threadpool

from src.services.email_templates import EmailContent, invite_email, reset_email

__all__ = ["EmailSender", "EmailService"]

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    """The one EmailClient method the service needs; tests stub it with a
    recording or raising fake."""

    def begin_send(self, message: Any) -> Any: ...


class EmailService:
    """Invite/reset emails via Azure Communication Services.

    `True` means ACS accepted the message for delivery (`begin_send` returns
    on the 202) — the LRO poller is deliberately not awaited: its status poll
    runs at ~10s intervals and a terminal "Succeeded" still doesn't prove
    mailbox delivery. Failures never propagate; the caller downgrades to the
    manual copy-the-link flow.
    """

    def __init__(
        self,
        sender: EmailSender,
        *,
        sender_address: str,
        app_url: str,
        entra_enabled: bool,
        invite_ttl_days: int,
        reset_ttl_days: int,
    ) -> None:
        self._sender = sender
        self._sender_address = sender_address
        self._app_url = app_url
        self._entra_enabled = entra_enabled
        self._invite_ttl_days = invite_ttl_days
        self._reset_ttl_days = reset_ttl_days

    async def send_invite_email(self, *, to: str, first_name: str, invite_link: str) -> bool:
        content = invite_email(
            first_name=first_name,
            invite_link=invite_link,
            ttl_days=self._invite_ttl_days,
            entra_enabled=self._entra_enabled,
            app_url=self._app_url,
        )
        return await self._send(to, content)

    async def send_reset_email(self, *, to: str, first_name: str, reset_link: str) -> bool:
        content = reset_email(
            first_name=first_name, reset_link=reset_link, ttl_days=self._reset_ttl_days
        )
        return await self._send(to, content)

    async def _send(self, to: str, content: EmailContent) -> bool:
        message = {
            "senderAddress": self._sender_address,
            "recipients": {"to": [{"address": to}]},
            "content": {
                "subject": content.subject,
                "plainText": content.plain_text,
                "html": content.html,
            },
        }
        try:
            # The SDK client is sync (requests) — never run it on the event loop.
            await run_in_threadpool(self._sender.begin_send, message)
        except Exception:
            logger.exception("email %r to %s failed", content.subject, to)
            return False
        return True
