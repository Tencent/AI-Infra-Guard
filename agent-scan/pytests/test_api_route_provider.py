"""Offline coverage for API Route's registry and shared OpenAI adapter path."""

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import yaml

from agent_scan.core.agent_adapter.adapter import (
    AIProviderClient,
    ProviderConfigLoader,
    ProviderOptions,
)


def test_openai_compatible_registries_stay_in_sync():
    root = Path(__file__).resolve().parents[1]
    registries = [
        yaml.safe_load(path.read_text(encoding="utf-8"))["providers"]["openai_compatible"]
        for path in (
            root / "providers.yaml",
            root / "agent_scan/core/agent_adapter/providers.yaml",
        )
    ]
    # Other format groups intentionally differ (e.g. custom HTTP vs. Dify).
    assert set(registries[0]["providers"]) == set(registries[1]["providers"])
    assert registries[0]["providers"]["api_route"] == registries[1]["providers"]["api_route"]


def test_api_route_provider_resolves():
    cfg = ProviderConfigLoader().get_provider_config("api_route")
    assert cfg is not None
    assert cfg["base_url"] == "https://global.api-route.com/v1"
    assert cfg["endpoint"] == "/chat/completions"
    assert cfg["default_model"] == "gpt-6.1-sol"
    assert cfg["env_keys"] == ["API_ROUTE_API_KEY"]
    assert cfg["models"] == [cfg["default_model"]]
    assert cfg["api_format"] == "openai"
    assert cfg["auth_type"] == "bearer"
    assert cfg["response_path"] == "choices[0].message.content"


@pytest.mark.parametrize(
    ("provider_id", "model"),
    [("api_route", "gpt-6.1-sol"), ("api_route:claude-fable-5-1", "claude-fable-5-1")],
)
def test_api_route_sends_authenticated_chat_request(monkeypatch, provider_id, model):
    monkeypatch.setenv("API_ROUTE_API_KEY", "api-route-test-key")
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "OK"}}]},
        request=httpx.Request("POST", "https://global.api-route.com/v1/chat/completions"),
    )
    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as transport:
        request = transport.return_value.__enter__.return_value.request
        request.return_value = response
        result = AIProviderClient(timeout=12).call_provider(
            ProviderOptions(id=provider_id), prompt="Reply OK"
        )

    assert result.success
    assert result.provider_response.output == "OK"
    assert result.provider_response.metadata["model"] == model
    assert result.provider_response.metadata["provider"] == "api_route"
    assert request.call_args.kwargs["method"] == "POST"
    assert request.call_args.kwargs["url"] == "https://global.api-route.com/v1/chat/completions"
    assert request.call_args.kwargs["headers"]["Authorization"] == "Bearer api-route-test-key"
    assert request.call_args.kwargs["json"]["model"] == model
    assert request.call_args.kwargs["json"]["messages"] == [{"role": "user", "content": "Reply OK"}]
    assert transport.call_args.kwargs["timeout"] == 12


def test_api_route_missing_key_does_not_use_another_provider_key(monkeypatch):
    monkeypatch.delenv("API_ROUTE_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "another-provider-key")
    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as transport:
        result = AIProviderClient().call_provider(ProviderOptions(id="api_route"))
    assert not result.success
    assert "API_ROUTE_API_KEY" in result.message
    transport.assert_not_called()
