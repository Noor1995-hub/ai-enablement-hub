"""Invite/reset email content.

Admins may customize the subject + Markdown body per project (see
`EmailTemplateService`); this module renders a resolved template to the ACS
`EmailContent` triple and validates admin-authored templates at save time.

Rendering is deliberately conservative: raw HTML in the Markdown source is
neutralized (`html=False`), user-derived token values are Markdown-escaped so a
stray `*` in a name can't reformat the message, and the action link is emitted
as a CommonMark autolink (`<url>`) so it renders clickable whether the admin
writes the token bare or as a `[label]({{invite_link}})` destination.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import NamedTuple

from src.services.exceptions import InvalidEmailTemplateError

__all__ = [
    "ALLOWED_TOKENS",
    "DEFAULT_TEMPLATES",
    "REQUIRED_LINK_TOKEN",
    "EmailContent",
    "EmailTemplate",
    "build_tokens",
    "render_email",
    "validate_template",
]

_STYLE = "font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #1a1a1a;"

# {{ token }} — lowercase/underscore names, optional inner whitespace.
_TOKEN_RE = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
# Markdown-active characters escaped in text token values (URLs are exempt).
_MD_ESCAPE_RE = re.compile(r"([\\`*_\[\]])")
# "[label](url)" -> "label: url" for the plain-text alternative.
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\((\S+?)\)")

# Tokens whose value is a URL — emitted as an autolink, never Markdown-escaped.
_LINK_TOKENS = frozenset({"invite_link", "reset_link", "login_url"})

_COMMON_TOKENS = ("first_name", "last_name", "project_name", "ttl_days")
ALLOWED_TOKENS: dict[str, tuple[str, ...]] = {
    "invite": (*_COMMON_TOKENS, "invite_link", "login_url"),
    "reset": (*_COMMON_TOKENS, "reset_link"),
}
REQUIRED_LINK_TOKEN = {"invite": "invite_link", "reset": "reset_link"}


class EmailContent(NamedTuple):
    subject: str
    plain_text: str
    html: str


class EmailTemplate(NamedTuple):
    subject: str
    body_markdown: str


def _days(ttl_days: int) -> str:
    return f"{ttl_days} day" + ("" if ttl_days == 1 else "s")


def _md_escape(value: str) -> str:
    return _MD_ESCAPE_RE.sub(r"\\\1", value)


def _substitute(template: str, tokens: Mapping[str, str], *, for_markdown: bool) -> str:
    """Replace {{token}} occurrences. In the Markdown pass link tokens become
    autolinks and text values are Markdown-escaped; the plain-text pass inserts
    raw values. Unknown tokens are left verbatim (validation blocks them on
    save, so this only guards render-time surprises)."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in tokens:
            return match.group(0)
        value = tokens[key]
        if not for_markdown:
            return value
        if key in _LINK_TOKENS:
            return f"<{value}>" if value else ""
        return _md_escape(value)

    return _TOKEN_RE.sub(repl, template)


def _render_markdown(markdown_source: str) -> str:
    # Imported lazily so the module stays importable (and unit-testable) without
    # markdown-it in trivial contexts; the dependency is a hard runtime require.
    from markdown_it import MarkdownIt

    md = MarkdownIt("commonmark", {"html": False})
    return md.render(markdown_source)


def render_email(subject: str, body_markdown: str, *, tokens: Mapping[str, str]) -> EmailContent:
    """Render a resolved template to the ACS (subject, plain_text, html) triple."""
    subject_out = _substitute(subject, tokens, for_markdown=False).strip()
    plain_out = _MD_LINK_RE.sub(
        r"\1: \2", _substitute(body_markdown, tokens, for_markdown=False)
    ).strip()
    html_body = _render_markdown(_substitute(body_markdown, tokens, for_markdown=True))
    html_out = f'<html><body style="{_STYLE}">{html_body}</body></html>'
    return EmailContent(subject_out, plain_out, html_out)


def build_tokens(
    purpose: str,
    *,
    first_name: str,
    last_name: str,
    project_name: str,
    link: str,
    ttl_days: int,
    login_url: str | None = None,
) -> dict[str, str]:
    """The substitution values for one send/preview, keyed by token name."""
    tokens = {
        "first_name": first_name,
        "last_name": last_name,
        "project_name": project_name,
        "ttl_days": _days(ttl_days),
        REQUIRED_LINK_TOKEN[purpose]: link,
    }
    if purpose == "invite":
        tokens["login_url"] = login_url or ""
    return tokens


def validate_template(purpose: str, subject: str, body_markdown: str) -> None:
    """Guard an admin-authored template at save time. Raises
    InvalidEmailTemplateError (→ 400) with a client-facing message."""
    if not subject.strip():
        raise InvalidEmailTemplateError("Subject must not be blank")
    if not body_markdown.strip():
        raise InvalidEmailTemplateError("Message body must not be blank")

    allowed = set(ALLOWED_TOKENS[purpose])
    used = set(_TOKEN_RE.findall(subject)) | set(_TOKEN_RE.findall(body_markdown))
    unknown = used - allowed
    if unknown:
        names = ", ".join(f"{{{{{token}}}}}" for token in sorted(unknown))
        raise InvalidEmailTemplateError(f"Unknown token(s): {names}")

    required = REQUIRED_LINK_TOKEN[purpose]
    if required not in _TOKEN_RE.findall(body_markdown):
        raise InvalidEmailTemplateError(
            f"The message body must include the {{{{{required}}}}} link token"
        )


DEFAULT_TEMPLATES: dict[str, EmailTemplate] = {
    "invite": EmailTemplate(
        subject="You're invited to the delaware AI Enablement Hub",
        body_markdown=(
            "Hi {{first_name}},\n\n"
            "You've been invited to the **AI Enablement Hub**, delaware's learning "
            "platform for the AI enablement programme.\n\n"
            "Set a password with your personal invite link:\n\n"
            "{{invite_link}}\n\n"
            "The invite link is valid for {{ttl_days}} and can be used once. "
            "If you weren't expecting this email, you can ignore it.\n"
        ),
    ),
    "reset": EmailTemplate(
        subject="Password reset for the AI Enablement Hub",
        body_markdown=(
            "Hi {{first_name}},\n\n"
            "An administrator issued a password reset link for your "
            "**AI Enablement Hub** account:\n\n"
            "{{reset_link}}\n\n"
            "The link is valid for {{ttl_days}} and can be used once. Your current "
            "password keeps working until you set a new one. "
            "If you weren't expecting this email, you can ignore it.\n"
        ),
    ),
}
