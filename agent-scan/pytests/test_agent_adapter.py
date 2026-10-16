import time
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from agent_scan.core.agent_adapter.adapter import AIProviderClient


def test_make_http_request_uses_transform_for_sse_chunks():
    sse = "\n\n".join([
        'data: {"stream":{"text":"Hello"},"answer":"Ignored"}',
        'data: {"stream":{"text":" World"},"answer":" ignored","usage":{"output_tokens":2}}',
        "data: [DONE]",
    ])
    response = SimpleNamespace(
        status_code=200,
        headers={"content-type": "text/event-stream"},
    )
    client = object.__new__(AIProviderClient)
    client.timeout = 30

    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as http_client:
        # The factory now streams the response; simulate a real SSE body that
        # iter_lines() would deliver chunk by chunk.
        stream_cm = http_client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value
        stream_cm.status_code = 200
        stream_cm.headers = {"content-type": "text/event-stream"}
        stream_cm.iter_lines.return_value = iter(sse.split("\n"))
        result = client._make_http_request(
            "https://example.test/agent", "POST", {}, {}, "stream.text"
        )

    assert result.success is True
    assert result.provider_response.output == "Hello World"
    assert result.provider_response.raw == {
        "content": "Hello World",
        "raw_sse": False,
        "usage": {"output_tokens": 2},
    }


def test_parse_sse_response_falls_back_when_transform_does_not_match():
    sse = "\n\n".join([
        'data: {"answer":"Hello"}',
        'data: {"answer":" World"}',
    ])
    client = object.__new__(AIProviderClient)

    response, _ = client._parse_sse_response(sse, "stream.text")

    assert response == {"content": "Hello World", "raw_sse": True}
    assert client._extract_output(response, "stream.text") == "Hello World"


def test_parse_sse_response_does_not_mix_fallback_after_transform_matches():
    sse = "\n\n".join([
        'data: {"stream":{"text":"Hello"}}',
        'data: {"answer":"STATUS"}',
    ])
    client = object.__new__(AIProviderClient)

    response, _ = client._parse_sse_response(sse, "stream.text")

    assert response == {"content": "Hello", "raw_sse": False}


def test_parse_sse_response_keeps_transformed_type_event_generic():
    sse = 'data: {"type":"chunk","stream":{"text":"Hello"}}'
    client = object.__new__(AIProviderClient)

    response, _ = client._parse_sse_response(sse, "stream.text")

    assert response == {"content": "Hello", "raw_sse": False}
    assert client._extract_output(response, "stream.text") == "Hello"


def test_make_http_request_streams_sse_body_even_when_connection_stays_open():
    """#707 regression: a real SSE endpoint holds the connection open and
    never closes it. The factory must consume the stream line by line and
    stop at the [DONE] marker instead of waiting for the connection to
    close."""
    lines = [
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        "",
        'data: {"choices":[{"delta":{"content":" World"}}]}',
        "",
        "data: [DONE]",
        "",
    ]
    client = object.__new__(AIProviderClient)
    client.timeout = 30

    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as http_client:
        stream_cm = http_client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value
        stream_cm.status_code = 200
        stream_cm.headers = {"content-type": "text/event-stream"}
        # After [DONE] the stream would keep the connection open (the iterable
        # could go on forever); the factory must break at [DONE].
        stream_cm.iter_lines.return_value = iter(lines)
        result = client._make_http_request(
            "https://example.test/agent", "POST", {}, {}, None
        )

    assert result.success is True
    assert result.provider_response.output == "Hello World"
    assert result.provider_response.raw["choices"][0]["message"]["content"] == "Hello World"
    # The streaming path must be used for SSE responses.
    http_client.return_value.__enter__.return_value.stream.assert_called_once()


def _sse_with_gap(lines_before, gap_seconds, lines_after):
    """Yield a scripted SSE stream with a real pause between two chunks."""
    for line in lines_before:
        yield line
    time.sleep(gap_seconds)
    for line in lines_after:
        yield line


def _make_client():
    client = object.__new__(AIProviderClient)
    client.timeout = 30
    return client


def test_make_http_request_sse_preserves_reply_across_thinking_gap():
    """#707 regression: a thinking pause between chunks used to be enforced as
    the per-chunk read timeout, silently killing the whole reply. The idle gap
    must be decoupled from the overall conversation budget so a reasoning model
    pausing to think is not truncated."""
    lines = _sse_with_gap(
        ['data: {"choices":[{"delta":{"content":"Hello"}}]}', ""],
        3.0,
        ['data: {"choices":[{"delta":{"content":" World"}}]}', "", "data: [DONE]", ""],
    )
    client = _make_client()

    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as http_client:
        stream_cm = http_client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value
        stream_cm.status_code = 200
        stream_cm.headers = {"content-type": "text/event-stream"}
        stream_cm.iter_lines.return_value = lines
        result = client._make_http_request(
            "https://example.test/agent", "POST", {}, {}, None,
            timeout_seconds=5.0, idle_timeout_seconds=60.0,
        )

    assert result.success is True
    assert result.provider_response.output == "Hello World"
    assert result.provider_response.metadata["budget_exceeded"] is False
    # The read (idle) timeout must be decoupled from the overall budget: a 3s
    # pause must not be fatal even though it exceeds the 5s budget slice-wise.
    timeout_arg = http_client.call_args.kwargs["timeout"]
    assert timeout_arg.read == 60.0
    assert timeout_arg.connect == 5.0


def test_make_http_request_sse_truncates_at_overall_budget():
    """The overall budget bounds the whole stream duration: when it is exceeded
    the already-received content is preserved (not dropped) and flagged, so the
    caller can still act on a partial reply instead of losing everything."""
    lines = _sse_with_gap(
        ['data: {"choices":[{"delta":{"content":"Hello"}}]}', ""],
        0.8,
        ['data: {"choices":[{"delta":{"content":" World"}}]}', "", "data: [DONE]", ""],
    )
    client = _make_client()

    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as http_client:
        stream_cm = http_client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value
        stream_cm.status_code = 200
        stream_cm.headers = {"content-type": "text/event-stream"}
        stream_cm.iter_lines.return_value = lines
        result = client._make_http_request(
            "https://example.test/agent", "POST", {}, {}, None,
            timeout_seconds=0.5, idle_timeout_seconds=60.0,
        )

    assert result.success is True
    assert result.provider_response.output == "Hello"
    assert result.provider_response.metadata["budget_exceeded"] is True
    assert "truncated" in result.message


def test_make_http_request_sse_stalled_stream_still_times_out():
    """A truly stalled stream (no chunk within the idle allowance) must still
    fail — the idle-gap relaxation must not turn every slow stream into a
    silent success."""

    def stalled():
        raise httpx.ReadTimeout("read timeout")
        yield  # pragma: no cover - makes this a generator

    client = _make_client()

    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as http_client:
        stream_cm = http_client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value
        stream_cm.status_code = 200
        stream_cm.headers = {"content-type": "text/event-stream"}
        stream_cm.iter_lines.return_value = stalled()
        result = client._make_http_request(
            "https://example.test/agent", "POST", {}, {}, None,
            timeout_seconds=30.0, idle_timeout_seconds=30.0,
        )

    assert result.success is False
    assert "timed out after 30" in result.message


def test_call_http_provider_passes_configured_timeout():
    """#613/#617 regression: the HTTP path must honor ``timeout_ms`` instead of
    silently using the adapter default, and default the SSE idle allowance to
    its own generous value."""
    from agent_scan.core.agent_adapter.adapter import (
        ProviderConfig,
        ProviderOptions,
        ProviderTestResult,
    )

    client = _make_client()
    provider = ProviderOptions(
        id="http:test",
        config=ProviderConfig(url="http://example.test/agent", timeout_ms=5000),
    )

    with patch.object(client, "_make_http_request", return_value=ProviderTestResult(success=True)) as mock_req:
        client._call_http_provider(provider, "hi")

    args, kwargs = mock_req.call_args
    assert kwargs["timeout_seconds"] == 5.0
    assert kwargs["idle_timeout_seconds"] == 60.0
