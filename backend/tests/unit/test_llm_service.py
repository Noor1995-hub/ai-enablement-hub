from __future__ import annotations

from src.services.llm_service import AnthropicLlmClient
from tests.fixtures.llm import FakeAsyncAnthropic


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
