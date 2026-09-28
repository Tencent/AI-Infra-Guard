"""Tests for adapters that wrap externally implemented agents."""

from pikit.agent import CallableAgentAdapter, DefenseHooks, Trace, TraceStep
from pikit.defenses import get


def test_callable_adapter_returns_text_as_trace():
    seen = {}

    def external_runner(message, **kwargs):
        seen["message"] = message
        seen["system"] = kwargs["system"]
        seen["taint"] = kwargs["taint"]
        return "external result"

    adapter = CallableAgentAdapter(
        external_runner,
        system="System instruction",
        taint={"fetch_url": "untrusted artifact"},
    )
    trace = adapter.run("Summarize this")
    assert trace.final_text == "external result"
    assert [step.kind for step in trace.steps] == ["system", "user", "model"]
    assert seen["message"] == "Summarize this"
    assert seen["system"] == "System instruction"
    assert seen["taint"]["fetch_url"] == "untrusted artifact"


def test_callable_adapter_applies_user_and_system_hooks():
    seen = {}

    def external_runner(message, **kwargs):
        seen["message"] = message
        seen["system"] = kwargs["system"]
        return "ok"

    hooks = DefenseHooks(
        user=get("delimiters")(),
        system=get("instructional")(),
    )
    CallableAgentAdapter(external_runner, system="Protect tools.", defenses=hooks).run(
        "Untrusted request"
    )
    assert "Untrusted request" in seen["message"]
    assert "Protect tools." in seen["system"]


def test_callable_adapter_preserves_external_trace():
    expected = Trace(
        steps=[TraceStep("tool_call", tool_name="send_email", is_sink=True)],
        final_text="done",
    )
    adapter = CallableAgentAdapter(lambda message, **kwargs: expected)
    assert adapter.run("go") is expected
