"""Tests for OpenClaw/Hermes terminal harness adapters."""

import json
import sys
from pathlib import Path

import pytest

from pikit.adapters import HermesCLIAdapter, OpenClawCLIAdapter
from pikit.runtime_assets import fixture_path
from pikit.agent import DefenseHooks
from pikit.defenses import get


def _fake_runtime_script(tmp_path, payload, *, exit_code=0):
    script = tmp_path / "fake_runtime.py"
    script.write_text(
        "import sys\n"
        f"print({payload!r})\n"
        f"raise SystemExit({exit_code})\n",
        encoding="utf-8",
    )
    return f"{sys.executable} {script}"


def test_openclaw_cli_adapter_builds_local_headless_command():
    adapter = OpenClawCLIAdapter(
        executable="openclaw",
        agent="research",
        model="deepseek-v4-flash",
        session_key="agent:research:test",
    )
    command = adapter.build_command("Summarize this")
    assert command[:4] == ["openclaw", "agent", "--local", "--json"]
    assert "--deliver" not in command
    assert "--channel" not in command
    assert command[command.index("--session-key") + 1] == "agent:research:test"
    assert command[command.index("--message") + 1] == "Summarize this"


def test_openclaw_cli_adapter_parses_json_output():
    adapter = OpenClawCLIAdapter(executable="openclaw")
    assert adapter.parse_output(json.dumps({"result": {"text": "done"}})) == "done"
    assert adapter.parse_output("diagnostic\n" + json.dumps({
        "payloads": [{"text": "done"}],
    }) + "\ntrailer") == "done"


def test_openclaw_cli_adapter_passes_isolated_state_paths(tmp_path):
    adapter = OpenClawCLIAdapter(
        executable="sh",
        state_dir=str(tmp_path / "state"),
        config_path=str(tmp_path / "state" / "openclaw.json"),
    )
    adapter.build_command = lambda message: [  # type: ignore[method-assign]
        "sh", "-c", "printf runtime"
    ]
    trace = adapter.run("request")
    assert trace.final_text == "runtime"


def test_hermes_cli_adapter_builds_safe_terminal_command():
    adapter = HermesCLIAdapter(
        executable="hermes",
        model="deepseek-v4-flash",
        provider="deepseek",
    )
    command = adapter.build_command("Summarize this")
    assert command[:3] == ["hermes", "--oneshot", "Summarize this"]
    assert "--safe-mode" in command
    assert command[command.index("--provider") + 1] == "deepseek"


def test_runtime_adapter_applies_user_defense_and_returns_trace(tmp_path):
    script = _fake_runtime_script(tmp_path, "runtime answer")
    adapter = HermesCLIAdapter(
        executable="sh",
        safe_mode=False,
        hermes_home=str(tmp_path / "hermes"),
        defenses=DefenseHooks(user=get("delimiters")()),
    )
    # Override command construction only for this subprocess contract test.
    adapter.build_command = lambda message: ["sh", "-c", f"{script}"]  # type: ignore[method-assign]
    trace = adapter.run("untrusted request")
    assert trace.final_text == "runtime answer"
    assert "untrusted request" in trace.steps[0].text


def test_runtime_adapter_reports_command_failure(tmp_path):
    script = _fake_runtime_script(tmp_path, "failure", exit_code=3)
    adapter = HermesCLIAdapter(executable="sh", safe_mode=False)
    adapter.build_command = lambda message: ["sh", "-c", f"{script}"]  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="exited with status 3"):
        adapter.run("request")


def test_runtime_adapter_imports_fixture_evidence(tmp_path):
    script = tmp_path / "fixture_runtime.py"
    script.write_text(
        "import json, os\n"
        "with open(os.environ['PIKIT_FIXTURE_TRACE_PATH'], 'w') as f:\n"
        " f.write(json.dumps({'type':'tool_result','tool':'pikit_read_document',"
        "'args':{'ref':'q3'},'content':'tainted','tainted':True}) + '\\n')\n"
        " f.write(json.dumps({'type':'sink_call','tool':'pikit_record_sink',"
        "'args':{'target':'attacker'}}) + '\\n')\n"
        "print('done')\n",
        encoding="utf-8",
    )
    adapter = HermesCLIAdapter(executable=sys.executable, safe_mode=False)
    adapter.build_command = lambda message: [sys.executable, str(script)]  # type: ignore[method-assign]
    trace = adapter.run("request", env={"PIKIT_FIXTURE_DOCUMENT": "tainted"})
    assert trace.tainted_steps[0].tool_name == "pikit_read_document"
    assert trace.sink_calls[0].args == {"target": "attacker"}


def test_runtime_fixture_assets_are_packaged_sources():
    assert (Path(fixture_path("openclaw")) / "package.json").is_file()
    assert (Path(fixture_path("hermes")) / "plugin.yaml").is_file()
