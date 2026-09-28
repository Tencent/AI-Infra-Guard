"""Setup and diagnostics for isolated OpenClaw and Hermes experiment profiles."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from .runtime_assets import fixture_path


def doctor(runtime: str, *, executable: str | None = None, home: str | None = None) -> Dict[str, Any]:
    """Inspect whether a runtime is ready for safe pikit fixture experiments."""
    runtime = runtime.lower()
    if runtime not in {"openclaw", "hermes"}:
        raise ValueError("runtime must be 'openclaw' or 'hermes'")
    executable = executable or runtime
    report: Dict[str, Any] = {
        "runtime": runtime,
        "executable": executable,
        "executable_found": bool(shutil.which(executable)),
        "fixture_path": fixture_path(runtime),
        "fixture_present": Path(fixture_path(runtime)).is_dir(),
        "profile": home or "",
    }
    if runtime == "openclaw":
        state = Path(home) if home else None
        report["config_present"] = bool(state and (state / "openclaw.json").is_file())
        report["fixture_built"] = bool(state and (state / "pikit-openclaw-fixture" / "dist" / "index.js").is_file())
        report["fixture_tools_expected"] = [
            "pikit_read_document", "pikit_fetch_url", "pikit_read_email",
            "pikit_search_knowledge", "pikit_load_skill", "pikit_record_sink",
        ]
        report["fixture_hint"] = (
            "Run `pikit runtime install-fixture openclaw <profile>` to build "
            "and link the fixture plugin."
        )
        report["fixture_loaded"] = False
        report["fixture_tools_visible"] = []
        if report["executable_found"] and report["config_present"]:
            env = os.environ.copy()
            env["OPENCLAW_STATE_DIR"] = str(state)
            env["OPENCLAW_CONFIG_PATH"] = str(state / "openclaw.json")
            probe = subprocess.run(
                [executable, "plugins", "inspect", "pikit-fixture", "--runtime", "--json"],
                env=env, capture_output=True, text=True, check=False,
            )
            if probe.returncode == 0:
                try:
                    payload = json.loads(probe.stdout)
                    report["fixture_loaded"] = payload.get("plugin", {}).get("status") == "loaded"
                    report["fixture_tools_visible"] = [
                        name for item in payload.get("tools", [])
                        for name in item.get("names", [])
                    ]
                except json.JSONDecodeError:
                    report["runtime_probe_error"] = "OpenClaw returned invalid plugin JSON"
            else:
                report["runtime_probe_error"] = probe.stderr.strip() or probe.stdout.strip()
    else:
        state = Path(home) if home else None
        report["config_present"] = bool(state and (state / "config.yaml").is_file())
        report["fixture_plugin_present"] = bool(
            state and (state / "plugins" / "pikit_fixture" / "plugin.yaml").is_file()
        )
        report["fixture_hint"] = (
            "The fixture plugin is copied by `pikit runtime init hermes`; "
            "run with `safe_mode=false` and `toolsets=['pikit_fixture']`."
        )
    report["ready"] = bool(
        report["executable_found"] and report["fixture_present"] and report["config_present"]
    )
    if runtime == "openclaw":
        report["ready"] = bool(
            report["ready"] and report["fixture_loaded"]
            and set(report["fixture_tools_expected"]).issubset(report["fixture_tools_visible"])
        )
    return report


def install_fixture(runtime: str, directory: str, *, executable: str | None = None) -> Dict[str, str]:
    """Build/install a fixture plugin into an isolated runtime profile."""
    runtime = runtime.lower()
    root = Path(directory).expanduser().resolve()
    if runtime == "hermes":
        init("hermes", str(root))
        return {
            "runtime": "hermes",
            "profile": str(root),
            "fixture": str(root / "plugins" / "pikit_fixture"),
            "status": "ready (plugin copied and enabled in config.yaml)",
        }
    if runtime != "openclaw":
        raise ValueError("runtime must be 'openclaw' or 'hermes'")
    init("openclaw", str(root))
    executable = executable or "openclaw"
    fixture = root / "pikit-openclaw-fixture"
    subprocess.run(["npm", "install"], cwd=fixture, check=True)
    subprocess.run(["npm", "run", "plugin:build"], cwd=fixture, check=True)
    env = os.environ.copy()
    env["OPENCLAW_STATE_DIR"] = str(root)
    env["OPENCLAW_CONFIG_PATH"] = str(root / "openclaw.json")
    subprocess.run([executable, "plugins", "install", str(fixture), "--link"], env=env, check=True)
    subprocess.run([executable, "plugins", "enable", "pikit-fixture"], env=env, check=True)
    subprocess.run([executable, "plugins", "registry", "--refresh"], env=env, check=True)
    return {
        "runtime": "openclaw",
        "profile": str(root),
        "fixture": str(fixture),
        "status": "built, linked, enabled, and registry refreshed",
    }


def init(runtime: str, directory: str) -> Dict[str, str]:
    """Create an isolated, fixture-only runtime profile skeleton.

    The command never writes provider credentials.  Operators configure model
    access separately through environment variables or the runtime's own
    onboarding flow.
    """
    runtime = runtime.lower()
    root = Path(directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if runtime == "hermes":
        plugin_dest = root / "plugins" / "pikit_fixture"
        if not plugin_dest.exists():
            shutil.copytree(fixture_path("hermes"), plugin_dest)
        config = root / "config.yaml"
        if not config.exists():
            config.write_text(
                "plugins:\n  enabled:\n    - pikit_fixture\n",
                encoding="utf-8",
            )
        return {
            "runtime": runtime,
            "profile": str(root),
            "config": str(config),
            "fixture": str(plugin_dest),
        }
    if runtime == "openclaw":
        fixture_dest = root / "pikit-openclaw-fixture"
        if not fixture_dest.exists():
            shutil.copytree(fixture_path("openclaw"), fixture_dest)
        config = root / "openclaw.json"
        if not config.exists():
            config.write_text(
                json.dumps(
                    {
                        "tools": {
                            "profile": "minimal",
                            "alsoAllow": [
                                "pikit_read_document", "pikit_fetch_url",
                                "pikit_read_email", "pikit_search_knowledge",
                                "pikit_load_skill", "pikit_record_sink",
                            ],
                            "deny": ["exec", "browser", "message", "write", "edit"],
                        }
                    },
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
        return {
            "runtime": runtime,
            "profile": str(root),
            "config": str(config),
            "fixture": str(fixture_dest),
        }
    raise ValueError("runtime must be 'openclaw' or 'hermes'")


__all__ = ["doctor", "init", "install_fixture"]
