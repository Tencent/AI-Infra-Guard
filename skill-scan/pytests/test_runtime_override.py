"""Regression tests for LLM environment overrides in the skill scanner."""

from skill_scan.main import parse_args, resolve_runtime_override


def test_llm_env_overrides_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("LLM_MODEL", "env-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://env.example/v1")

    args = parse_args([])

    assert resolve_runtime_override(args)[1:] == (
        "env-model",
        "https://env.example/v1",
    )


def test_cli_flags_take_precedence_over_env(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "env-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://env.example/v1")

    args = parse_args(["--model", "cli-model", "--base_url", "https://cli.example/v1"])

    assert resolve_runtime_override(args)[1:] == (
        "cli-model",
        "https://cli.example/v1",
    )
