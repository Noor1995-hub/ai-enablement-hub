from __future__ import annotations

import logging
from typing import Any, Protocol

from starlette.concurrency import run_in_threadpool

from src.services.email_templates import EmailContent

__all__ = ["EmailSender", "EmailService"]

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    """The one EmailClient method the service needs; tests stub it with a
    recording or raising fake."""

    def begin_send(self, message: Any) -> Any: ...


class EmailService:
    """Transport for pre-rendered emails via Azure Communication Services.

    Content (subject/plain/html) is produced upstream by EmailTemplateService so
    this class stays a thin, project-agnostic ACS adapter.

    `True` means ACS accepted the message for delivery (`begin_send` returns on
    the 202) — the LRO poller is deliberately not awaited: its status poll runs
    at ~10s intervals and a terminal "Succeeded" still doesn't prove mailbox
    delivery. Failures never propagate; the caller downgrades to the manual
    copy-the-link flow.
    """

    def __init__(self, sender: EmailSender, *, sender_address: str) -> None:
        self._sender = sender
        self._sender_address = sender_address

    async def send(self, to: str, content: EmailContent) -> bool:
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
