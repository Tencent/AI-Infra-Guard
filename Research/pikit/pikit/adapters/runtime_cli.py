"""Safe, headless adapters for installed agent runtimes.

These adapters are intentionally process boundaries rather than imports of
runtime internals. They make it possible to test terminal-only deployments
without enabling chat channels, Docker, shell tools, or real delivery sinks.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from ..agent.base import Trace, TraceStep
from ..agent.hooks import DefenseHooks
from .harness import AgentHarness, register_harness


class RuntimeCLIAdapter(AgentHarness):
    """Base class for a one-shot, headless agent-runtime command.

    Subclasses implement :meth:`build_command`. The process receives a
    hardened user message and returns its captured stdout as final text unless
    a runtime-specific parser extracts a structured final response.

    No command is executed until :meth:`run` is called. The adapter never
    enables a messaging channel or delivery flag on its own.
    """

    name = "runtime_cli"

    def __init__(
        self,
        executable: str,
        *,
        system: Optional[str] = None,
        defenses: Optional[DefenseHooks] = None,
        timeout: int = 120,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        self.executable = executable
        self.system = system
        self.hooks = defenses or DefenseHooks()
        self.timeout = timeout
        self.env = dict(env or {})

    def is_available(self) -> bool:
        """Return whether the configured runtime executable is on ``PATH``."""
        return shutil.which(self.executable) is not None

    def build_command(self, user_message: str) -> list:
        """Build the non-interactive command for one agent turn."""
        raise NotImplementedError

    def parse_output(self, stdout: str) -> str:
        """Return final text from command stdout; subclasses may override."""
        return stdout.strip()

    def run(self, user_message: str, **kwargs: Any) -> Trace:
        """Run the runtime in a subprocess and translate it into a trace."""
        if not self.is_available():
            raise FileNotFoundError(
                f"{self.executable!r} was not found on PATH; install the "
                f"runtime or pass executable=..."
            )

        system = self.hooks.on_system(self.system)
        message = self.hooks.on_user(user_message)
        env = os.environ.copy()
        env.update(self.env)
        env.update({str(k): str(v) for k, v in kwargs.pop("env", {}).items()})
        fixture_payloads = kwargs.pop("fixture_payloads", None)
        if fixture_payloads is not None:
            env["PIKIT_FIXTURE_PAYLOADS"] = json.dumps(fixture_payloads)
        fixture_trace_path = env.get("PIKIT_FIXTURE_TRACE_PATH")
        temporary_fixture_trace = None
        if not fixture_trace_path and (
            env.get("PIKIT_FIXTURE_DOCUMENT") is not None or fixture_payloads is not None
        ):
            handle = tempfile.NamedTemporaryFile(
                prefix="pikit-fixture-", suffix=".jsonl", delete=False
            )
            handle.close()
            fixture_trace_path = handle.name
            temporary_fixture_trace = handle.name
            env["PIKIT_FIXTURE_TRACE_PATH"] = fixture_trace_path

        try:
            completed = subprocess.run(
                self.build_command(message),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=kwargs.pop("timeout", self.timeout),
                env=env,
                check=False,
                **kwargs,
            )
            if completed.returncode != 0:
                detail = completed.stderr.strip() or completed.stdout.strip()
                raise RuntimeError(
                    f"{self.name} exited with status {completed.returncode}: {detail}"
                )

            final_text = self.parse_output(completed.stdout)
            trace = Trace()
            if system:
                trace.add(TraceStep("system", text=system))
            trace.add(TraceStep("user", text=message))
            self._append_fixture_events(trace, fixture_trace_path)
            trace.add(TraceStep("model", text=final_text))
            trace.final_text = final_text
            return trace
        finally:
            if temporary_fixture_trace:
                try:
                    os.unlink(temporary_fixture_trace)
                except FileNotFoundError:
                    pass

    @staticmethod
    def _append_fixture_events(trace: Trace, path: Optional[str]) -> None:
        """Map safe fixture-plugin JSONL evidence into pikit's standard trace."""
        if not path or not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type")
                tool = str(event.get("tool", "fixture"))
                args = event.get("args")
                if event_type == "tool_result":
                    trace.add(TraceStep(
                        "tool_call",
                        tool_name=tool,
                        args=args if isinstance(args, dict) else {},
                    ))
                    trace.add(TraceStep(
                        "tool_result",
                        tool_name=tool,
                        content=str(event.get("content", "")),
                        tainted=bool(event.get("tainted", False)),
                    ))
                elif event_type == "sink_call":
                    trace.add(TraceStep(
                        "tool_call",
                        tool_name=tool,
                        args=args if isinstance(args, dict) else {},
                        is_sink=True,
                    ))
                elif event_type in {"policy_block", "approval_requested", "tool_error"}:
                    trace.add(TraceStep(
                        "tool_result",
                        tool_name=tool,
                        content=str(event.get("reason", event_type)),
                        decision=event_type,
                    ))


@register_harness("openclaw")
class OpenClawCLIAdapter(RuntimeCLIAdapter):
    """Run one local, headless OpenClaw agent turn through its CLI.

    The adapter invokes ``openclaw agent --local --json``. It never supplies
    ``--deliver`` or a channel, so OpenClaw's messaging integrations are not
    involved. Use a dedicated OpenClaw profile/configuration that only exposes
    test fixture tools when evaluating indirect injection.
    """

    name = "openclaw"

    def __init__(
        self,
        executable: str = "openclaw",
        *,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        session_key: Optional[str] = "agent:main:pikit",
        thinking: Optional[str] = None,
        state_dir: Optional[str] = None,
        config_path: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(executable, **kwargs)
        self.agent = agent
        self.model = model
        self.session_key = session_key
        self.thinking = thinking
        self.state_dir = state_dir
        self.config_path = config_path

    def build_command(self, user_message: str) -> list:
        command = [
            self.executable, "agent", "--local", "--json", "--message", user_message,
        ]
        if self.agent:
            command.extend(["--agent", self.agent])
        if self.model:
            command.extend(["--model", self.model])
        if self.session_key:
            command.extend(["--session-key", self.session_key])
        if self.thinking:
            command.extend(["--thinking", self.thinking])
        return command

    def parse_output(self, stdout: str) -> str:
        payload = _parse_json_payload(stdout)
        if payload is None:
            return super().parse_output(stdout)
        return _extract_text(payload) or super().parse_output(stdout)

    def run(self, user_message: str, **kwargs: Any) -> Trace:
        """Run with optional isolated OpenClaw state/config paths.

        A configured provider is still required. The adapter does not perform
        onboarding because provider credentials and tool policy belong to the
        researcher's explicitly managed test profile.
        """
        env = dict(kwargs.pop("env", {}))
        if self.state_dir:
            env["OPENCLAW_STATE_DIR"] = self.state_dir
        if self.config_path:
            env["OPENCLAW_CONFIG_PATH"] = self.config_path
        return super().run(user_message, env=env, **kwargs)


@register_harness("hermes")
class HermesCLIAdapter(RuntimeCLIAdapter):
    """Run one non-interactive Hermes CLI turn without messaging channels.

    ``hermes --oneshot`` works directly in a terminal. By default the
    adapter adds ``--safe-mode`` to disable user customizations, skills,
    plugins, and MCP servers. Set ``safe_mode=False`` only with a dedicated
    isolated Hermes profile and an explicit tool policy.
    """

    name = "hermes"

    def __init__(
        self,
        executable: str = "hermes",
        *,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        toolsets: Optional[Iterable[str]] = None,
        safe_mode: bool = True,
        hermes_home: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(executable, **kwargs)
        self.model = model
        self.provider = provider
        self.toolsets = list(toolsets or [])
        self.safe_mode = safe_mode
        self.hermes_home = hermes_home

    def build_command(self, user_message: str) -> list:
        command = [self.executable, "--oneshot", user_message]
        if self.safe_mode:
            command.append("--safe-mode")
        if self.model:
            command.extend(["--model", self.model])
        if self.provider:
            command.extend(["--provider", self.provider])
        if self.toolsets:
            command.extend(["--toolsets", ",".join(self.toolsets)])
        return command

    def run(self, user_message: str, **kwargs: Any) -> Trace:
        # A temporary HERMES_HOME prevents ordinary test runs from reading or
        # modifying the user's persistent sessions, memory, or credentials.
        if self.hermes_home:
            return super().run(
                user_message,
                env={**kwargs.pop("env", {}), "HERMES_HOME": self.hermes_home},
                **kwargs,
            )
        with tempfile.TemporaryDirectory(prefix="pikit-hermes-") as home:
            return super().run(
                user_message,
                env={**kwargs.pop("env", {}), "HERMES_HOME": str(Path(home))},
                **kwargs,
            )


def _extract_text(value: Any) -> str:
    """Best-effort extraction across OpenClaw JSON output versions."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "output", "response", "content", "message", "payloads"):
            text = _extract_text(value.get(key))
            if text:
                return text
        for key in ("result", "data"):
            text = _extract_text(value.get(key))
            if text:
                return text
    if isinstance(value, list):
        return "\n".join(filter(None, (_extract_text(item) for item in value)))
    return ""


def _parse_json_payload(text: str) -> Any:
    """Find the first JSON value in noisy runtime stdout."""
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
            if isinstance(value, (dict, list)):
                return value
        except json.JSONDecodeError:
            continue
    return None


__all__ = [
    "RuntimeCLIAdapter",
    "OpenClawCLIAdapter",
    "HermesCLIAdapter",
]
