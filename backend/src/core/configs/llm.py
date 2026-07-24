from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr

__all__ = ["LlmSettings"]


class LlmSettings(BaseModel):
    """Anthropic API settings; env prefix `LLM__` (see Settings).

    All three fields are required: setting one `LLM__*` variable with the others
    missing must fail startup loudly, never half-enable the feature (mirrors
    EmailSettings).
    """

    model_config = ConfigDict(frozen=True)

    provider: str
    model: str
    api_key: SecretStr
