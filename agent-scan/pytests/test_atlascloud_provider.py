"""Offline coverage for Atlas Cloud's registry and shared OpenAI adapter path."""

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
    assert set(registries[0]["providers"]) == set(registries[1]["providers"])
    assert registries[0]["providers"]["atlascloud"] == registries[1]["providers"]["atlascloud"]


def test_atlascloud_provider_resolves():
    cfg = ProviderConfigLoader().get_provider_config("atlascloud")
    assert cfg is not None
    assert cfg["base_url"] == "https://api.atlascloud.ai/v1"
    assert cfg["endpoint"] == "/chat/completions"
    assert cfg["default_model"] == "deepseek-ai/deepseek-v4-flash"
    assert cfg["env_keys"] == ["ATLASCLOUD_API_KEY"]
    assert cfg["default_model"] in cfg["models"]
    assert cfg["api_format"] == "openai"
    assert cfg["auth_type"] == "bearer"
    assert cfg["response_path"] == "choices[0].message.content"


@pytest.mark.parametrize(
    ("provider_id", "model"),
    [
        ("atlascloud", "deepseek-ai/deepseek-v4-flash"),
        ("atlascloud:moonshotai/kimi-k3", "moonshotai/kimi-k3"),
    ],
)
def test_atlascloud_sends_authenticated_chat_request(monkeypatch, provider_id, model):
    monkeypatch.setenv("ATLASCLOUD_API_KEY", "atlas-test-key")
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "OK"}}]},
        request=httpx.Request("POST", "https://api.atlascloud.ai/v1/chat/completions"),
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
    assert result.provider_response.metadata["provider"] == "atlascloud"
    assert request.call_args.kwargs["method"] == "POST"
    assert request.call_args.kwargs["url"] == "https://api.atlascloud.ai/v1/chat/completions"
    assert request.call_args.kwargs["headers"]["Authorization"] == "Bearer atlas-test-key"
    assert request.call_args.kwargs["json"]["model"] == model
    assert request.call_args.kwargs["json"]["messages"] == [{"role": "user", "content": "Reply OK"}]
    assert transport.call_args.kwargs["timeout"] == 12


def test_atlascloud_missing_key_does_not_use_another_provider_key(monkeypatch):
    monkeypatch.delenv("ATLASCLOUD_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "another-provider-key")
    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as transport:
        result = AIProviderClient().call_provider(ProviderOptions(id="atlascloud"))
    assert not result.success
    assert "ATLASCLOUD_API_KEY" in result.message
    transport.assert_not_called()
