"""Tests for the CLI module."""

import subprocess
import sys
import json


def _run_cli(*args):
    """Run pikit CLI as a subprocess and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "pikit.cli", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def test_cli_list():
    code, stdout, _ = _run_cli("list")
    assert code == 0
    assert "attacks" in stdout
    assert "defenses" in stdout
    assert "channels" in stdout


def test_cli_show_attacks():
    code, stdout, _ = _run_cli("show", "attacks")
    assert code == 0
    assert "naive" in stdout


def test_cli_show_defenses():
    code, stdout, _ = _run_cli("show", "defenses")
    assert code == 0
    assert "sandwich" in stdout or "spotlighting" in stdout


def test_cli_show_channels():
    code, stdout, _ = _run_cli("show", "channels")
    assert code == 0
    assert "webpage" in stdout


def test_cli_run_supports_offline_mock_target():
    code, stdout, stderr = _run_cli(
        "run",
        "--target", "mock",
        "--agent", "chat",
        "--attack", "naive",
        "--task", "Reply with exactly: CLI_OK",
    )
    assert code == 0, stderr
    assert "target=mock" in stdout
    assert "CLI_OK" in stdout


def test_cli_runtime_init_and_doctor(tmp_path):
    profile = tmp_path / "hermes"
    code, stdout, stderr = _run_cli("runtime", "init", "hermes", str(profile), "--json")
    assert code == 0, stderr
    assert json.loads(stdout)["runtime"] == "hermes"
    code, stdout, stderr = _run_cli("runtime", "doctor", "hermes", str(profile), "--json")
    assert code == 0, stderr
    assert json.loads(stdout)["fixture_plugin_present"] is True


def test_cli_report_jsonl(tmp_path):
    results = tmp_path / "results.jsonl"
    results.write_text(
        json.dumps({
            "agent": "chat", "attack": "naive", "channel": "",
            "defense": "none", "success": True, "signals": ["canary_terse"],
            "trace": ">>> model: HACKED",
        }) + "\n",
        encoding="utf-8",
    )
    code, stdout, stderr = _run_cli("report", str(results))
    assert code == 0, stderr
    assert "Full successes" in stdout


def test_cli_runtime_rejects_python_only_harnesses():
    code, _, _ = _run_cli("run", "--runtime", "langchain")
    assert code != 0
