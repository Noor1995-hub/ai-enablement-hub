from __future__ import annotations

import html
from typing import NamedTuple

__all__ = ["EmailContent", "invite_email", "reset_email"]

_STYLE = "font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #1a1a1a;"


class EmailContent(NamedTuple):
    subject: str
    plain_text: str
    html: str


def _days(ttl_days: int) -> str:
    return f"{ttl_days} day" + ("" if ttl_days == 1 else "s")


def invite_email(
    *, first_name: str, invite_link: str, ttl_days: int, entra_enabled: bool, app_url: str
) -> EmailContent:
    """Invitation to the hub. With Entra enabled the primary path is Microsoft
    sign-in (the login page only shows that button when the backend reports it,
    so we link `{app_url}/login`, never the OIDC endpoint directly); the invite
    link stays as the set-a-password fallback."""
    subject = "You're invited to the delaware AI Enablement Hub"
    login_url = f"{app_url.rstrip('/')}/login"
    intro = (
        f"Hi {first_name},\n\n"
        "You've been invited to the AI Enablement Hub, delaware's learning "
        "platform for the AI enablement programme.\n\n"
    )
    footer = (
        f"\nThe invite link is valid for {_days(ttl_days)} and can be used once.\n"
        "If you weren't expecting this email, you can ignore it.\n"
    )
    if entra_enabled:
        body = (
            "There are two ways to get started:\n\n"
            f"1. Sign in with your Microsoft account: {login_url}\n"
            f"2. Or set a password with your personal invite link:\n   {invite_link}\n"
        )
    else:
        body = f"Set a password with your personal invite link:\n{invite_link}\n"
    plain_text = intro + body + footer

    name_h = html.escape(first_name)
    link_h = html.escape(invite_link)
    login_h = html.escape(login_url)
    if entra_enabled:
        body_h = (
            "<p>There are two ways to get started:</p>"
            f'<ol><li>Sign in with your Microsoft account: <a href="{login_h}">{login_h}</a></li>'
            "<li>Or set a password with your personal invite link:<br>"
            f'<a href="{link_h}">{link_h}</a></li></ol>'
        )
    else:
        body_h = (
            "<p>Set a password with your personal invite link:<br>"
            f'<a href="{link_h}">{link_h}</a></p>'
        )
    html_body = (
        f'<html><body style="{_STYLE}">'
        f"<p>Hi {name_h},</p>"
        "<p>You've been invited to the <strong>AI Enablement Hub</strong>, "
        "delaware's learning platform for the AI enablement programme.</p>"
        f"{body_h}"
        f"<p>The invite link is valid for {_days(ttl_days)} and can be used once.<br>"
        "If you weren't expecting this email, you can ignore it.</p>"
        "</body></html>"
    )
    return EmailContent(subject, plain_text, html_body)


def reset_email(*, first_name: str, reset_link: str, ttl_days: int) -> EmailContent:
    subject = "Password reset for the AI Enablement Hub"
    plain_text = (
        f"Hi {first_name},\n\n"
        "An administrator issued a password reset link for your AI Enablement "
        "Hub account:\n\n"
        f"{reset_link}\n\n"
        f"The link is valid for {_days(ttl_days)} and can be used once. Your "
        "current password keeps working until you set a new one.\n"
        "If you weren't expecting this email, you can ignore it.\n"
    )
    name_h = html.escape(first_name)
    link_h = html.escape(reset_link)
    html_body = (
        f'<html><body style="{_STYLE}">'
        f"<p>Hi {name_h},</p>"
        "<p>An administrator issued a password reset link for your "
        "<strong>AI Enablement Hub</strong> account:</p>"
        f'<p><a href="{link_h}">{link_h}</a></p>'
        f"<p>The link is valid for {_days(ttl_days)} and can be used once. "
        "Your current password keeps working until you set a new one.<br>"
        "If you weren't expecting this email, you can ignore it.</p>"
        "</body></html>"
    )
    return EmailContent(subject, plain_text, html_body)
