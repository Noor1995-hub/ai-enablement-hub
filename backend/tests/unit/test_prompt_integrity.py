"""What the admin editor used to check on save now runs in CI on every PR."""

import pytest

from src.services import prompts as P
from src.services.prompt_service import KNOWN_PROMPTS, REQUIRED_TOKENS


@pytest.mark.parametrize("kind", [m.kind for m in KNOWN_PROMPTS])
def test_every_known_prompt_has_a_non_empty_file(kind: str) -> None:
    assert P.read_file(kind)


@pytest.mark.parametrize(
    ("kind", "token"), [(k, t) for k, tokens in REQUIRED_TOKENS.items() for t in tokens]
)
def test_required_tokens_are_present(kind: str, token: str) -> None:
    assert token in P.read_file(kind), f"{kind}.md lost required placeholder {token}"
