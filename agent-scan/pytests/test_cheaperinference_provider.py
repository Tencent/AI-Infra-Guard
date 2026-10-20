"""Offline coverage for Cheaper Inference's registry and shared OpenAI adapter path."""

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


def test_cheaperinference_registries_stay_in_sync():
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
        registries[0]["providers"]["cheaperinference"]
        == registries[1]["providers"]["cheaperinference"]
    )


def test_cheaperinference_provider_resolves():
    cfg = ProviderConfigLoader().get_provider_config("cheaperinference")
    assert cfg is not None
    assert cfg["base_url"] == "https://api.cheaperinference.com/v1"
    assert cfg["endpoint"] == "/chat/completions"
    assert cfg["default_model"] == "gpt-5.4-mini"
    assert cfg["env_keys"] == ["CHEAPER_INFERENCE_API_KEY"]
    assert cfg["default_model"] in cfg["models"]
    assert cfg["api_format"] == "openai"
    assert cfg["auth_type"] == "bearer"
    assert cfg["response_path"] == "choices[0].message.content"


@pytest.mark.parametrize(
    ("provider_id", "model"),
    [
        ("cheaperinference", "gpt-5.4-mini"),
        ("cheaperinference:claude-sonnet-5", "claude-sonnet-5"),
    ],
)
def test_cheaperinference_sends_authenticated_chat_request(monkeypatch, provider_id, model):
    monkeypatch.setenv("CHEAPER_INFERENCE_API_KEY", "ci-test-key")
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "OK"}}]},
        request=httpx.Request("POST", "https://api.cheaperinference.com/v1/chat/completions"),
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
    assert result.provider_response.metadata["provider"] == "cheaperinference"
    assert stream_method.call_args.kwargs["method"] == "POST"
    assert stream_method.call_args.kwargs["url"] == "https://api.cheaperinference.com/v1/chat/completions"
    assert stream_method.call_args.kwargs["headers"]["Authorization"] == "Bearer ci-test-key"
    assert stream_method.call_args.kwargs["json"]["model"] == model
    assert stream_method.call_args.kwargs["json"]["messages"] == [{"role": "user", "content": "Reply OK"}]
    assert transport.call_args.kwargs["timeout"] == 12


def test_cheaperinference_missing_key_does_not_use_another_provider_key(monkeypatch):
    monkeypatch.delenv("CHEAPER_INFERENCE_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "another-provider-key")
    with patch("agent_scan.core.agent_adapter.adapter.httpx.Client") as transport:
        result = AIProviderClient().call_provider(ProviderOptions(id="cheaperinference"))
    assert not result.success
    assert "CHEAPER_INFERENCE_API_KEY" in result.message
    transport.assert_not_called()
