from types import SimpleNamespace
from unittest.mock import patch

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
        text=sse,
    )
    client = object.__new__(AIProviderClient)
    client.timeout = 30

    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as http_client:
        http_client.return_value.__enter__.return_value.request.return_value = response
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
