import pytest

from src.services.llm_service import StructuredSchema
from tests.golden.ai import harness
from tests.golden.ai.harness import RecordingLlm, assert_golden, render_calls


async def test_recording_llm_records_both_call_shapes():
    llm = RecordingLlm(structured_results=[{"a": 1}], chunks=["hi"])
    async with llm.stream_reply(
        system="S", messages=[{"role": "user", "content": "u"}], max_tokens=5
    ) as s:
        assert [c async for c in s] == ["hi"]
    schema = StructuredSchema(name="tool", description="d", input_schema={"type": "object"})
    out, _ = await llm.complete_structured(system="S2", prompt="P", schema=schema, max_tokens=7)
    assert out == {"a": 1}
    assert [c["method"] for c in llm.calls] == ["stream_reply", "complete_structured"]


def test_render_is_readable_and_stable():
    calls = [
        {
            "method": "stream_reply",
            "system": "line1\nline2",
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 5,
        },
    ]
    text = render_calls(calls)
    assert "=== call 1: stream_reply (max_tokens=5) ===" in text
    assert "--- system ---\nline1\nline2\n" in text
    assert "--- message 1 (user) ---\nhello\n" in text
    assert render_calls(calls) == text


def test_missing_snapshot_fails_with_instructions(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.delenv("UPDATE_GOLDEN", raising=False)
    monkeypatch.delenv("CI", raising=False)
    with pytest.raises(AssertionError, match="UPDATE_GOLDEN=1"):
        assert_golden("nope", [])


def test_update_golden_writes_then_plain_run_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "SNAPSHOT_DIR", tmp_path)
    calls = [{"method": "stream_reply", "system": "S", "messages": [], "max_tokens": 1}]
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("UPDATE_GOLDEN", "1")
    assert_golden("x", calls)
    monkeypatch.delenv("UPDATE_GOLDEN")
    assert_golden("x", calls)
    calls[0]["system"] = "changed"
    with pytest.raises(AssertionError):
        assert_golden("x", calls)


def test_update_golden_is_ignored_in_ci(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setenv("UPDATE_GOLDEN", "1")
    monkeypatch.setenv("CI", "true")
    with pytest.raises(AssertionError):
        assert_golden("never-written", [])
