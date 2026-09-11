from unittest.mock import patch

from mcp_scan.utils.llm import LLM, to_litellm_params


def _make_llm(model="gpt-5.5", api_key="sk-test", base_url="https://gw.example/v1"):
    llm = object.__new__(LLM)
    llm.model = model
    llm.api_key = api_key
    llm.base_url = base_url
    return llm


def test_to_litellm_params_openai_compatible_when_base_url_set():
    assert to_litellm_params(
        "deepseek/deepseek-v3.2-exp", "https://openrouter.ai/api/v1"
    ) == ("openai/deepseek/deepseek-v3.2-exp", "https://openrouter.ai/api/v1")
    assert to_litellm_params("openai/gpt-4o", "https://gw/v1") == (
        "openai/gpt-4o",
        "https://gw/v1",
    )


def test_to_litellm_params_native_when_no_base_url():
    assert to_litellm_params("anthropic/claude-sonnet-4.5", None) == (
        "anthropic/claude-sonnet-4.5",
        None,
    )
    assert to_litellm_params("bedrock/anthropic.claude-3", "") == (
        "bedrock/anthropic.claude-3",
        None,
    )


def test_chat_stream_routes_through_litellm_with_drop_params():
    llm = _make_llm()
    with patch("mcp_scan.utils.llm.litellm.completion", return_value=[]) as completion:
        assert llm.chat_stream([{"role": "user", "content": "test"}]) == ("", None)

    assert completion.call_count == 1
    kwargs = completion.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-5.5"
    assert kwargs["api_base"] == "https://gw.example/v1"
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["stream"] is True
    assert kwargs["drop_params"] is True
    # usage accounting is preserved via stream_options.
    assert kwargs["stream_options"] == {"include_usage": True}
    assert "temperature" not in kwargs


def test_chat_stream_native_provider_when_base_url_blank():
    llm = _make_llm(model="anthropic/claude-sonnet-4.5", base_url="")
    with patch("mcp_scan.utils.llm.litellm.completion", return_value=[]) as completion:
        llm.chat_stream([{"role": "user", "content": "hi"}])

    kwargs = completion.call_args.kwargs
    assert kwargs["model"] == "anthropic/claude-sonnet-4.5"
    assert kwargs["api_base"] is None
