"""A transient LLM failure must be retried instead of failing the whole scan.

``LLM.chat_stream`` raises ``TimeoutError`` when a streamed response exceeds
``stream_timeout``; connection errors, 429 and 5xx come from the OpenAI SDK.
Before the retry, any of these ended the scan task immediately.
"""

from __future__ import annotations

import httpx
import openai
import pytest

from skill_scan.utils import llm as llm_module
from skill_scan.utils.llm import LLM

_REQ = httpx.Request("POST", "http://127.0.0.1:9/v1/chat/completions")
_DEADLINE = TimeoutError("LLM streaming response exceeded the 300-second deadline")


def _status_error(cls, code):
    return cls(str(code), response=httpx.Response(code, request=_REQ), body=None)


@pytest.fixture
def sleeps(monkeypatch):
    calls: list[float] = []
    monkeypatch.setattr(llm_module.time, "sleep", calls.append)
    return calls


def _llm(monkeypatch, outcomes):
    llm = LLM("test-model", "k", "http://127.0.0.1:9/v1")
    attempts: list[int] = []

    def fake_stream(message):
        attempts.append(1)
        item = outcomes[len(attempts) - 1]
        if isinstance(item, BaseException):
            raise item
        return item, {"total_tokens": 1}

    monkeypatch.setattr(llm, "chat_stream", fake_stream)
    return llm, attempts


@pytest.mark.parametrize(
    "error",
    [
        _DEADLINE,
        openai.APIConnectionError(request=_REQ),
        _status_error(openai.InternalServerError, 502),
    ],
    ids=["stream_deadline", "connection", "5xx"],
)
def test_transient_error_is_retried(monkeypatch, sleeps, error):
    llm, attempts = _llm(monkeypatch, [error, "done"])

    assert llm.chat([]) == "done"
    assert len(attempts) == 2
    assert sleeps == [1.0]


def test_retry_gives_up_after_five_trials(monkeypatch, sleeps):
    llm, attempts = _llm(monkeypatch, [_DEADLINE] * 5)

    with pytest.raises(TimeoutError):
        llm.chat([])
    assert len(attempts) == 5
    assert sleeps == [1.0, 2.0, 4.0, 8.0]


def test_rate_limit_backs_off_longer(monkeypatch, sleeps):
    rate_limited = _status_error(openai.RateLimitError, 429)
    llm, _ = _llm(monkeypatch, [rate_limited, rate_limited, "done"])

    assert llm.chat([]) == "done"
    assert sleeps == [8.0, 16.0]


def test_authentication_error_is_not_retried(monkeypatch, sleeps):
    llm, attempts = _llm(monkeypatch, [_status_error(openai.AuthenticationError, 401), "done"])

    with pytest.raises(openai.AuthenticationError):
        llm.chat([])
    assert len(attempts) == 1
    assert sleeps == []


def test_empty_reply_handling_is_unchanged(monkeypatch, sleeps):
    llm, attempts = _llm(monkeypatch, ["", "done"])

    assert llm.chat([]) == "done"
    assert len(attempts) == 2
    assert sleeps == [1.3]


def test_retried_reply_is_still_normalized(monkeypatch, sleeps):
    hex_finish = "<tool_call:6124c78e>finish>\n<parameter=content>ok</parameter>\n</function>"
    llm, _ = _llm(monkeypatch, [_DEADLINE, hex_finish])

    assert "<function=finish>" in llm.chat([])
