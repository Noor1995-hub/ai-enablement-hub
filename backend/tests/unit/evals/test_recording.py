from __future__ import annotations

from evals.interviewer.recording import RecordingLlmClient
from tests.fixtures.llm import FakeLlmClient


async def test_recording_client_keeps_every_call_in_order() -> None:
    inner = FakeLlmClient(chunks=[], structured={"shared": {"a": 1}})
    recorder = RecordingLlmClient(inner)

    result, usage = await recorder.complete_structured(
        system="s1",
        prompt="p1",
        schema=object(),
        max_tokens=10,
    )
    await recorder.complete_structured(
        system="s2",
        prompt="p2",
        schema=object(),
        max_tokens=10,
    )

    assert result == {"shared": {"a": 1}}
    assert recorder.model == "fake-model"
    assert len(recorder.calls) == 2
    assert recorder.calls[0] == {
        "system": "s1",
        "prompt": "p1",
        "raw_output": {"shared": {"a": 1}},
        "usage": usage,
    }
    assert recorder.calls[1]["system"] == "s2"


async def test_recording_client_delegates_stream_reply_unrecorded() -> None:
    """simulate.py uses stream_reply (the opener/chat calls); `run` never does. Delegate
    plainly rather than recording it, so RecordingLlmClient satisfies LlmClient without
    pretending stream_reply matters to a playbook run."""
    inner = FakeLlmClient(chunks=["hi"])
    recorder = RecordingLlmClient(inner)

    async with recorder.stream_reply(system="s", messages=[], max_tokens=10) as reply:
        chunks = [c async for c in reply]

    assert chunks == ["hi"]
    assert recorder.calls == []
