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
    # #96: end each interview chat turn at the interviewer's first question that ends a
    # paragraph (services/interview_stop.py), so it can't go on to write the learner's
    # answer. Off until the eval shows it cuts only what it should;
    # LLM__INTERVIEW_HARD_STOP=true turns it on.
    interview_hard_stop: bool = False
