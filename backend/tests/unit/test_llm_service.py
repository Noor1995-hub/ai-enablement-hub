from __future__ import annotations

from src.services.llm_service import AnthropicLlmClient, StructuredSchema
from tests.fixtures.llm import FakeAsyncAnthropic, FakeStructuredAsyncAnthropic


async def test_anthropic_client_streams_chunks_and_reports_usage() -> None:
    fake_sdk = FakeAsyncAnthropic(chunks=["Hel", "lo!"], usage=(12, 3))
    client = AnthropicLlmClient(
        fake_sdk,  # ty: ignore[invalid-argument-type]
        model="claude-haiku-4-5",
    )

    collected: list[str] = []
    async with client.stream_reply(
        system="You are helpful.", messages=[{"role": "user", "content": "hi"}], max_tokens=1024
    ) as reply:
        async for chunk in reply:
            collected.append(chunk)
        usage = await reply.usage()

    assert collected == ["Hel", "lo!"]
    assert usage.input_tokens == 12
    assert usage.output_tokens == 3


async def test_anthropic_client_complete_structured_returns_tool_input_and_usage() -> None:
    fake_sdk = FakeStructuredAsyncAnthropic(
        tool_input={"suggested_status": "accepted", "rationale": "actionable"},
        usage=(20, 8),
    )
    client = AnthropicLlmClient(
        fake_sdk,  # ty: ignore[invalid-argument-type]
        model="claude-haiku-4-5",
    )
    schema = StructuredSchema(
        name="triage",
        description="Suggest a triage disposition.",
        input_schema={
            "type": "object",
            "properties": {
                "suggested_status": {"type": "string", "enum": ["accepted", "dismissed"]},
                "rationale": {"type": "string"},
            },
            "required": ["suggested_status", "rationale"],
            "additionalProperties": False,
        },
    )

    result, usage = await client.complete_structured(
        system="You triage feedback.",
        prompt="Feedback: the examples were unclear.",
        schema=schema,
        max_tokens=512,
    )

    assert result == {"suggested_status": "accepted", "rationale": "actionable"}
    assert usage.input_tokens == 20
    assert usage.output_tokens == 8
    # forced tool_use wired with the schema's tool name + the client's model
    call = fake_sdk.messages.calls[0]
    assert call["tool_choice"] == {"type": "tool", "name": "triage"}
    assert call["model"] == "claude-haiku-4-5"
    assert call["tools"][0]["name"] == "triage"  # ty: ignore[not-subscriptable]
