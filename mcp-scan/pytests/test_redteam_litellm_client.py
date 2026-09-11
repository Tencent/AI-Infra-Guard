import asyncio
from unittest.mock import AsyncMock, patch

from mcp_scan.utils.llm import LiteLLMAsyncClient


def test_litellm_async_client_routes_through_acompletion():
    """The red-team async client shim must forward calls to litellm.acompletion
    with the same OpenAI-compatible routing the sync path uses."""
    client = LiteLLMAsyncClient(api_key="sk-test", base_url="https://gw/v1", timeout=90)

    with patch(
        "mcp_scan.utils.llm.litellm.acompletion",
        new=AsyncMock(return_value="resp"),
    ) as acompletion:
        result = asyncio.run(
            client.chat.completions.create(
                model="deepseek/deepseek-v3.2-exp",
                messages=[{"role": "user", "content": "hi"}],
            )
        )

    assert result == "resp"
    kwargs = acompletion.call_args.kwargs
    assert kwargs["model"] == "openai/deepseek/deepseek-v3.2-exp"
    assert kwargs["api_base"] == "https://gw/v1"
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["timeout"] == 90
    assert kwargs["drop_params"] is True


def test_litellm_async_client_native_routing_without_base_url():
    client = LiteLLMAsyncClient(api_key="sk-test", base_url="", timeout=90)

    with patch(
        "mcp_scan.utils.llm.litellm.acompletion",
        new=AsyncMock(return_value="resp"),
    ) as acompletion:
        asyncio.run(
            client.chat.completions.create(
                model="anthropic/claude-sonnet-4.5",
                messages=[{"role": "user", "content": "hi"}],
            )
        )

    kwargs = acompletion.call_args.kwargs
    assert kwargs["model"] == "anthropic/claude-sonnet-4.5"
    assert kwargs["api_base"] is None
