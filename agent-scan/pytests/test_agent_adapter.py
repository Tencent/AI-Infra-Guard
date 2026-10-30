from types import SimpleNamespace
from unittest.mock import patch

from agent_scan.core.agent_adapter.adapter import (
    _agui_terminal_event,
    AIProviderClient,
)


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


def test_parse_sse_response_skips_null_content_deltas():
    # Tool-call chunks, and DeepSeek reasoning chunks, carry "content": null.
    sse = "\n\n".join([
        'data: {"choices":[{"delta":{"role":"assistant","content":null,"reasoning_content":"Think"}}]}',
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
        "data: [DONE]",
    ])
    client = object.__new__(AIProviderClient)

    response, _ = client._parse_sse_response(sse)

    assert response["choices"][0]["message"]["content"] == "Hello"
    assert response["choices"][0]["finish_reason"] == "stop"


def test_parse_sse_response_handles_usage_only_final_chunk():
    # With stream_options.include_usage, the last chunk has "choices": [].
    sse = "\n\n".join([
        'data: {"choices":[{"delta":{"role":"assistant","content":"Hello"}}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
        'data: {"choices":[],"usage":{"prompt_tokens":5,"completion_tokens":1,"total_tokens":6}}',
        "data: [DONE]",
    ])
    client = object.__new__(AIProviderClient)

    response, usage = client._parse_sse_response(sse)

    assert response["choices"][0]["message"]["content"] == "Hello"
    assert response["choices"][0]["finish_reason"] == "stop"
    assert usage == {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6}


def test_agui_terminal_event_only_recognizes_run_lifecycle():
    """AG-UI terminal detection must not misclassify other SSE payloads."""
    assert _agui_terminal_event('data: {"type":"RUN_FINISHED","threadId":"t1"}') == "RUN_FINISHED"
    assert _agui_terminal_event('data: {"type":"RUN_ERROR","error":{"message":"boom"}}') == "RUN_ERROR"
    # Not terminal / not AG-UI.
    assert _agui_terminal_event('data: {"type":"TEXT_MESSAGE_CONTENT","delta":"hi"}') is None
    assert _agui_terminal_event("data: [DONE]") is None
    assert _agui_terminal_event("data: plain text") is None
    assert _agui_terminal_event("data: {invalid json") is None
    assert _agui_terminal_event("event: run_finished") is None


def test_make_http_request_parses_agui_stream_stopping_at_run_finished():
    """#699: AG-UI streams end with RUN_FINISHED (not OpenAI [DONE]) — the
    factory must consume TEXT_MESSAGE_CONTENT deltas and stop at the terminal
    event instead of waiting for the connection to close."""
    lines = [
        'data: {"type":"RUN_STARTED","threadId":"t1","runId":"r1"}',
        "",
        'data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"m1","delta":"Hello"}',
        "",
        'data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"m1","delta":" World"}',
        "",
        'data: {"type":"RUN_FINISHED","threadId":"t1","runId":"r1","usage":{"output_tokens":2}}',
        "",
        # Simulate a connection that would keep producing lines after the run
        # finished — the factory must break at RUN_FINISHED.
        'data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"m2","delta":"IGNORED"}',
    ]
    client = object.__new__(AIProviderClient)
    client.timeout = 30

    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as http_client:
        stream_cm = http_client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value
        stream_cm.status_code = 200
        stream_cm.headers = {"content-type": "text/event-stream"}
        stream_cm.iter_lines.return_value = iter(lines)
        result = client._make_http_request(
            "https://example.test/agent", "POST", {}, {}, None
        )

    assert result.success is True
    assert result.provider_response.output == "Hello World"
    assert result.provider_response.raw["content"] == "Hello World"
    assert result.provider_response.raw["protocol"] == "agui"
    assert result.provider_response.raw["usage"] == {"output_tokens": 2}


def test_make_http_request_surfaces_agui_run_error():
    """AG-UI RUN_ERROR must be surfaced as a failed result, not dropped."""
    lines = [
        'data: {"type":"RUN_STARTED","threadId":"t1","runId":"r1"}',
        "",
        'data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"m1","delta":"Hello"}',
        "",
        'data: {"type":"RUN_ERROR","threadId":"t1","runId":"r1","error":{"message":"agent crashed"}}',
        "",
    ]
    client = object.__new__(AIProviderClient)
    client.timeout = 30

    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as http_client:
        stream_cm = http_client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value
        stream_cm.status_code = 200
        stream_cm.headers = {"content-type": "text/event-stream"}
        stream_cm.iter_lines.return_value = iter(lines)
        result = client._make_http_request(
            "https://example.test/agent", "POST", {}, {}, None
        )

    assert result.success is False
    assert "agent crashed" in result.message
    assert result.provider_response.output == "Hello"
    assert result.provider_response.raw["run_error"] == "agent crashed"
    assert result.provider_response.raw["protocol"] == "agui"
