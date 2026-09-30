from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr

__all__ = ["LlmSettings"]


class LlmSettings(BaseModel):
    """Anthropic API settings; env prefix `LLM__` (see Settings).

    Both fields are required: setting one `LLM__*` variable with the other
    missing must fail startup loudly, never half-enable the feature (mirrors
    EmailSettings).

    There is deliberately no `provider` field: nothing ever read it (the app always
    builds `AnthropicLlmClient`). A stale `LLM__PROVIDER` is ignored, not rejected
    (this class is a plain pydantic `BaseModel`, which ignores unknown keys by default;
    `Settings`' own `extra="ignore"` only covers top-level keys; see
    tests/unit/test_llm_settings.py).
    """

    model_config = ConfigDict(frozen=True)

    model: str
    api_key: SecretStr
