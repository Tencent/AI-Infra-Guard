from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent_scan.utils.llm import LLM


def test_chat_request_omits_temperature():
    create = Mock(return_value=[])
    llm = object.__new__(LLM)
    llm.model = "gpt-5.5"
    llm.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    assert list(llm.chat_stream([{"role": "user", "content": "test"}])) == []
    assert create.call_count == 1
    assert "temperature" not in create.call_args.kwargs


def _heartbeat_llm(monkeypatch, module):
    class HeartbeatStream:
        def __init__(self):
            self.closed = False

        def __iter__(self):
            # Empty heartbeat chunks keep the SDK read timeout from firing; the
            # clock below passes the deadline on the second one.
            for _ in range(5):
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
    times = iter([0, 100, 301])
    monkeypatch.setattr(f"{module}.time.monotonic", lambda: next(times))
    monkeypatch.setattr(f"{module}.time.sleep", lambda _seconds: None)
    return llm, response


def test_chat_stream_stops_heartbeat_only_response_after_deadline(monkeypatch):
    llm, response = _heartbeat_llm(monkeypatch, "agent_scan.utils.llm")

    with pytest.raises(TimeoutError, match="300-second deadline"):
        list(llm.chat_stream([{"role": "user", "content": "test"}]))
    assert response.closed


def test_chat_returns_error_instead_of_hanging_on_heartbeat_stream(monkeypatch):
    llm, response = _heartbeat_llm(monkeypatch, "agent_scan.utils.llm")

    result = llm.chat([{"role": "user", "content": "test"}], language="en")

    assert "300-second deadline" in result
    assert response.closed
