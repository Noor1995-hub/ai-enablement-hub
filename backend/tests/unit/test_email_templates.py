"""Per-project email template rendering + validation: token substitution,
Markdown → HTML (raw HTML neutralized), link placement (bare + labeled),
plain-text output, and save-time validation of the token vocabulary."""

from __future__ import annotations

import pytest

from src.services.email_templates import (
    ALLOWED_TOKENS,
    DEFAULT_TEMPLATES,
    build_tokens,
    render_email,
    validate_template,
)
from src.services.exceptions import InvalidEmailTemplateError

LINK = "http://testserver:5173/invite/tok_ABC-123"


def _invite_tokens(**overrides: str) -> dict[str, str]:
    tokens = {
        "first_name": "Sarah",
        "last_name": "Jones",
        "project_name": "Acme Onboarding",
        "ttl_days": "7 days",
        "invite_link": LINK,
        "login_url": "http://testserver:5173/login",
    }
    tokens.update(overrides)
    return tokens


class TestRenderTokens:
    def test_text_tokens_fill_subject_and_body(self) -> None:
        content = render_email(
            "Welcome {{first_name}}", "Hi {{first_name}} {{last_name}}", tokens=_invite_tokens()
        )
        assert content.subject == "Welcome Sarah"
        assert "Hi Sarah Jones" in content.plain_text
        assert "Hi Sarah Jones" in content.html

    def test_project_name_and_ttl_tokens(self) -> None:
        content = render_email(
            "s", "{{project_name}} — valid {{ttl_days}}. {{invite_link}}", tokens=_invite_tokens()
        )
        assert "Acme Onboarding — valid 7 days." in content.plain_text
        assert "Acme Onboarding" in content.html
        assert "7 days" in content.html


class TestLinkPlacement:
    def test_bare_link_token_renders_a_clickable_url(self) -> None:
        content = render_email("s", "Set it up:\n\n{{invite_link}}", tokens=_invite_tokens())
        assert f'<a href="{LINK}">{LINK}</a>' in content.html
        # Plain text keeps the raw URL, not an anchor.
        assert LINK in content.plain_text
        assert "<a" not in content.plain_text

    def test_labeled_link_token_renders_the_label(self) -> None:
        content = render_email("s", "[Set your password]({{invite_link}})", tokens=_invite_tokens())
        assert f'<a href="{LINK}">Set your password</a>' in content.html
        # Plain text flattens "[label](url)" to a readable "label: url".
        assert f"Set your password: {LINK}" in content.plain_text

    def test_link_can_sit_anywhere_the_admin_places_it(self) -> None:
        content = render_email("s", "top\n\n{{invite_link}}\n\nbottom", tokens=_invite_tokens())
        html = content.html
        assert html.index("top") < html.index(LINK) < html.index("bottom")


class TestMarkdown:
    def test_bold_and_lists_render_to_html(self) -> None:
        content = render_email(
            "s", "Hi **there**\n\n- one\n- two\n\n{{invite_link}}", tokens=_invite_tokens()
        )
        assert "<strong>there</strong>" in content.html
        assert "<li>one</li>" in content.html

    def test_house_style_wrapper(self) -> None:
        content = render_email("s", "{{invite_link}}", tokens=_invite_tokens())
        assert content.html.startswith("<html><body style=")
        assert content.html.rstrip().endswith("</body></html>")


class TestSafety:
    def test_raw_html_in_body_is_neutralized(self) -> None:
        content = render_email(
            "s", "<script>alert(1)</script>\n\n{{invite_link}}", tokens=_invite_tokens()
        )
        assert "<script>" not in content.html
        assert "&lt;script&gt;" in content.html

    def test_markdown_specials_in_a_token_value_do_not_format(self) -> None:
        # A name with emphasis characters must render literally, not italicized.
        content = render_email(
            "s", "Hi {{first_name}}\n\n{{invite_link}}", tokens=_invite_tokens(first_name="a*b*c")
        )
        assert "a*b*c" in content.html
        assert "<em>" not in content.html


class TestValidate:
    def test_valid_invite_template_passes(self) -> None:
        validate_template("invite", "Welcome", "Hi {{first_name}}\n\n{{invite_link}}")

    def test_body_without_the_link_token_is_rejected(self) -> None:
        with pytest.raises(InvalidEmailTemplateError):
            validate_template("invite", "Welcome", "Hi {{first_name}} — no link here")

    def test_reset_requires_its_own_link_token(self) -> None:
        with pytest.raises(InvalidEmailTemplateError):
            validate_template("reset", "Reset", "Use {{invite_link}}")  # wrong link token
        validate_template("reset", "Reset", "Use {{reset_link}}")

    def test_unknown_token_is_rejected(self) -> None:
        with pytest.raises(InvalidEmailTemplateError):
            validate_template("invite", "Hi {{unknown_thing}}", "{{invite_link}}")

    def test_blank_subject_or_body_is_rejected(self) -> None:
        with pytest.raises(InvalidEmailTemplateError):
            validate_template("invite", "   ", "{{invite_link}}")
        with pytest.raises(InvalidEmailTemplateError):
            validate_template("invite", "Hi", "   ")

    def test_login_url_is_allowed_only_for_invite(self) -> None:
        assert "login_url" in ALLOWED_TOKENS["invite"]
        assert "login_url" not in ALLOWED_TOKENS["reset"]


class TestDefaults:
    @pytest.mark.parametrize("purpose", ["invite", "reset"])
    def test_default_templates_are_valid(self, purpose: str) -> None:
        template = DEFAULT_TEMPLATES[purpose]
        validate_template(purpose, template.subject, template.body_markdown)

    def test_default_invite_renders_with_the_link(self) -> None:
        template = DEFAULT_TEMPLATES["invite"]
        content = render_email(template.subject, template.body_markdown, tokens=_invite_tokens())
        assert LINK in content.plain_text
        assert f'href="{LINK}"' in content.html


class TestBuildTokens:
    def test_invite_tokens_include_link_and_login(self) -> None:
        tokens = build_tokens(
            "invite",
            first_name="Sarah",
            last_name="Jones",
            project_name="Acme",
            link=LINK,
            ttl_days=7,
            login_url="http://x/login",
        )
        assert tokens["invite_link"] == LINK
        assert tokens["login_url"] == "http://x/login"
        assert tokens["ttl_days"] == "7 days"

    def test_reset_tokens_use_reset_link_and_singular_day(self) -> None:
        tokens = build_tokens(
            "reset",
            first_name="Res",
            last_name="Et",
            project_name="Acme",
            link=LINK,
            ttl_days=1,
        )
        assert tokens["reset_link"] == LINK
        assert "login_url" not in tokens
        assert tokens["ttl_days"] == "1 day"
