from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from azure.communication.email import EmailClient
from fastapi import Depends

# Runtime imports on purpose: FastAPI must resolve these names when it
# evaluates the deferred parameter annotations below (see database.py).
from src.core.configs.settings import Settings
from src.core.dependencies.settings import get_settings
from src.services.email_service import EmailService

__all__ = ["get_email_service"]


@lru_cache
def _email_client(connection_string: str) -> EmailClient:
    """Process-lifetime client. No retries and bounded timeouts: the send runs
    inside the admin's request, so a dead ACS endpoint must fail fast (the
    endpoint then reports email_status="failed" and the admin copies the link)."""
    # ty sees EmailClient as a union of the generated class and azure's `_patch` re-export and
    # does not find the classmethod on the generated half; the call is the documented API.
    return EmailClient.from_connection_string(  # ty: ignore[unresolved-attribute]
        connection_string, retry_total=0, connection_timeout=5, read_timeout=10
    )


def get_email_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmailService | None:
    """None (not 404) when EMAIL__* is unconfigured: unlike Entra, the
    invite/reset endpoints exist either way — they just skip the send."""
    if settings.email is None:
        return None
    return EmailService(
        _email_client(settings.email.connection_string.get_secret_value()),
        sender_address=settings.email.sender_address,
    )
