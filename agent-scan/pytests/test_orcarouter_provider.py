"""Smoke tests for the orcarouter provider registration.

The orcarouter entry mirrors the existing openrouter entry in the provider
registries. These tests make sure the registry entry resolves to the expected
base_url/endpoint so a wrong default string can't surface as a 404 at scan time.
"""

from agent_scan.core.agent_adapter.adapter import ProviderConfigLoader


def test_orcarouter_provider_resolves():
    cfg = ProviderConfigLoader().get_provider_config("orcarouter")
    assert cfg is not None, "orcarouter not found in providers.yaml registry"
    assert cfg["base_url"] == "https://api.orcarouter.ai/v1"
    assert cfg["endpoint"] == "/chat/completions"
    assert cfg["default_model"] == "orcarouter/fusion"
    assert "ORCAROUTER_API_KEY" in cfg["env_keys"]
    assert "orcarouter/fusion" in cfg["models"]
    assert "orcarouter/fusion-flash" in cfg["models"]
    assert "orcarouter/fusion-mini" in cfg["models"]
