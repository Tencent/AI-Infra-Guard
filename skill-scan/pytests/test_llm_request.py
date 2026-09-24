from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from skill_scan.utils.llm import LLM


@pytest.mark.parametrize(
    ("setting", "expected"),
    [("high", "high"), (" medium ", "medium"), (None, None), ("", None), (" \t ", None)],
)
def test_chat_request_uses_optional_reasoning_effort(monkeypatch, setting, expected):
    if setting is None:
        monkeypatch.delenv("REASONING_EFFORT", raising=False)
    else:
        monkeypatch.setenv("REASONING_EFFORT", setting)
    create = Mock(return_value=[])
    llm = object.__new__(LLM)
    llm.model = "test-reasoning-model"
    llm.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    llm.chat_stream([{"role": "user", "content": "test"}])

    if expected is None:
        assert "reasoning_effort" not in create.call_args.kwargs
    else:
        assert create.call_args.kwargs["reasoning_effort"] == expected


def test_chat_request_omits_temperature():
    create = Mock(return_value=[])
    llm = object.__new__(LLM)
    llm.model = "gpt-5.5"
    llm.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    assert llm.chat_stream([{"role": "user", "content": "test"}]) == ("", None)
    assert create.call_count == 1
    assert "temperature" not in create.call_args.kwargs


def test_chat_stream_stops_heartbeat_only_response_after_deadline(monkeypatch):
    class HeartbeatStream:
        def __init__(self):
            self.closed = False

        def __iter__(self):
            yield SimpleNamespace(usage=None, choices=[])

        def close(self):
            self.closed = True

    response = HeartbeatStream()
    llm = object.__new__(LLM)
    llm.model = "deepseek-v4-flash"
    llm.stream_timeout = 300
    llm.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=Mock(return_value=response))
        )
    )
    times = iter([0, 301])
    monkeypatch.setattr("skill_scan.utils.llm.time.monotonic", lambda: next(times))

    with pytest.raises(TimeoutError, match="300-second deadline"):
        llm.chat_stream([{"role": "user", "content": "test"}])
    assert response.closed
