from __future__ import annotations

from evals.interviewer.recording import RecordingLlmClient, UsageCapturingLlmClient
from src.services.llm_service import LlmUsage
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


async def test_recording_client_records_a_streamed_call_once_it_is_read() -> None:
    """The playbook is a streamed tagged document since #149: the runner bills it, checks the
    served model and stop reason, and grades the raw text, so the stream is recorded too."""
    usage = LlmUsage(input_tokens=7, output_tokens=3, model="m", stop_reason="end_turn")
    inner = FakeLlmClient(chunks=["<shared>", "</shared>"], usage=usage)
    recorder = RecordingLlmClient(inner)

    async with recorder.stream_reply(
        system="s", messages=[{"role": "user", "content": "write it"}], max_tokens=10
    ) as reply:
        chunks = [c async for c in reply]
        reported = await reply.usage()

    assert chunks == ["<shared>", "</shared>"]
    assert reported == usage
    assert recorder.calls == [
        {"system": "s", "prompt": "write it", "raw_output": "<shared></shared>", "usage": usage}
    ]


async def test_usage_capturing_client_captures_usage_even_when_the_caller_never_asks() -> None:
    """InterviewService.open_interview never calls `reply.usage()` (it only reads the
    streamed text) - the wrapper must still capture usage once the iterator is
    exhausted, or the opener's cost would be silently missed."""
    usage = LlmUsage(input_tokens=7, output_tokens=3, model="fake-served-model")
    inner = FakeLlmClient(chunks=["hi", " there"], usage=usage)
    usages: list[LlmUsage] = []
    client = UsageCapturingLlmClient(inner, usages)

    async with client.stream_reply(system="s", messages=[], max_tokens=10) as reply:
        chunks = [c async for c in reply]
        # open_interview never calls reply.usage() at all.

    assert chunks == ["hi", " there"]
    assert usages == [usage]


async def test_usage_capturing_client_captures_usage_exactly_once_when_the_caller_also_asks() -> (
    None
):
    """ChatService.send_message *does* call `reply.usage()` after the loop - usage must
    not be recorded twice (that would double-bill the call)."""
    usage = LlmUsage(input_tokens=7, output_tokens=3)
    inner = FakeLlmClient(chunks=["hi"], usage=usage)
    usages: list[LlmUsage] = []
    client = UsageCapturingLlmClient(inner, usages)

    async with client.stream_reply(system="s", messages=[], max_tokens=10) as reply:
        async for _ in reply:
            pass
        asked_usage = await reply.usage()

    assert asked_usage == usage
    assert usages == [usage]


async def test_usage_capturing_client_records_every_call_in_order() -> None:
    """Both the interviewer's and the learner's calls in one simulation share a single
    `usages` list on two separate wrapper instances (spec 2026-09-28), so the total cost
    of the simulation is the sum of everything in it, in call order."""
    interviewer_inner = FakeLlmClient(chunks=["Q1"], usage=LlmUsage(1, 1))
    learner_inner = FakeLlmClient(chunks=["A1"], usage=LlmUsage(2, 2))
    usages: list[LlmUsage] = []
    interviewer = UsageCapturingLlmClient(interviewer_inner, usages)
    learner = UsageCapturingLlmClient(learner_inner, usages)

    async with interviewer.stream_reply(system="s", messages=[], max_tokens=10) as reply:
        async for _ in reply:
            pass
    async with learner.stream_reply(system="s", messages=[], max_tokens=10) as reply:
        async for _ in reply:
            pass

    assert usages == [LlmUsage(1, 1), LlmUsage(2, 2)]
    assert interviewer.model == "fake-model"
