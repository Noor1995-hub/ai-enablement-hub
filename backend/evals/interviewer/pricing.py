"""USD cost of one attempt, from recorded usage. A price change here never touches how
the eval calls the model."""

from __future__ import annotations

__all__ = ["PRICE_PER_MTOK", "UnknownModelError", "cost_usd"]


class UnknownModelError(RuntimeError):
    """No price on file for this model - refuse to under-report cost silently."""


# USD per million tokens, (input, output): Anthropic first-party prices for claude-sonnet-5 as of
# 2026-06 ($2 in / $10 out). Re-check before a paid run (spec §6 touchpoint 3).
PRICE_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (2.0, 10.0),
    # Used only by this package's own tests (FakeLlmClient.model == "fake-model");
    # harmless in production, since the real client never reports this model id.
    "fake-model": (1.0, 1.0),
}


def cost_usd(*, model: str, input_tokens: int, output_tokens: int) -> float:
    if model not in PRICE_PER_MTOK:
        raise UnknownModelError(f"No price on file for {model!r}; add it to PRICE_PER_MTOK first.")
    price_in, price_out = PRICE_PER_MTOK[model]
    return (input_tokens / 1_000_000) * price_in + (output_tokens / 1_000_000) * price_out
