"""Offline coverage for cheapaimodel's registry and shared OpenAI adapter path."""

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


def test_cheapaimodel_registries_stay_in_sync():
    root = Path(__file__).resolve().parents[1]
    registries = [
        yaml.safe_load(path.read_text(encoding="utf-8"))["providers"]["openai_compatible"]
        for path in (
            root / "providers.yaml",
            root / "agent_scan/core/agent_adapter/providers.yaml",
        )
    ]
    assert set(registries[0]["providers"]) == set(registries[1]["providers"])
    assert (
        registries[0]["providers"]["cheapaimodel"]
        == registries[1]["providers"]["cheapaimodel"]
    )


def test_cheapaimodel_provider_resolves():
    cfg = ProviderConfigLoader().get_provider_config("cheapaimodel")
    assert cfg is not None
    assert cfg["base_url"] == "https://api.cheapaimodel.ai/v1"
    assert cfg["endpoint"] == "/chat/completions"
    assert cfg["default_model"] == "deepseek-v4-1-flash"
    assert cfg["env_keys"] == ["CHEAPAIMODEL_API_KEY"]
    assert cfg["default_model"] in cfg["models"]
    assert cfg["api_format"] == "openai"
    assert cfg["auth_type"] == "bearer"
    assert cfg["response_path"] == "choices[0].message.content"


@pytest.mark.parametrize(
    ("provider_id", "model"),
    [
        ("cheapaimodel", "deepseek-v4-1-flash"),
        ("cheapaimodel:kimi-k3", "kimi-k3"),
    ],
)
def test_cheapaimodel_sends_authenticated_chat_request(monkeypatch, provider_id, model):
    monkeypatch.setenv("CHEAPAIMODEL_API_KEY", "cam-test-key")
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "OK"}}]},
        request=httpx.Request("POST", "https://api.cheapaimodel.ai/v1/chat/completions"),
    )
    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as transport:
        stream_method = transport.return_value.__enter__.return_value.stream
        stream_cm = stream_method.return_value.__enter__.return_value
        stream_cm.status_code = 200
        stream_cm.headers = {"content-type": "application/json"}
        stream_cm.text = response.text
        stream_cm.json = lambda: response.json()
        result = AIProviderClient(timeout=12).call_provider(
            ProviderOptions(id=provider_id), prompt="Reply OK"
        )

    assert result.success
    assert result.provider_response.output == "OK"
    assert result.provider_response.metadata["model"] == model
    assert result.provider_response.metadata["provider"] == "cheapaimodel"
    assert stream_method.call_args.kwargs["method"] == "POST"
    assert stream_method.call_args.kwargs["url"] == "https://api.cheapaimodel.ai/v1/chat/completions"
    assert stream_method.call_args.kwargs["headers"]["Authorization"] == "Bearer cam-test-key"
    assert stream_method.call_args.kwargs["json"]["model"] == model
    assert stream_method.call_args.kwargs["json"]["messages"] == [{"role": "user", "content": "Reply OK"}]
    assert transport.call_args.kwargs["timeout"] == 12


def test_cheapaimodel_missing_key_does_not_use_another_provider_key(monkeypatch):
    monkeypatch.delenv("CHEAPAIMODEL_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "another-provider-key")
    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as transport:
        result = AIProviderClient().call_provider(ProviderOptions(id="cheapaimodel"))
    assert not result.success
    assert "CHEAPAIMODEL_API_KEY" in result.message
    transport.assert_not_called()
