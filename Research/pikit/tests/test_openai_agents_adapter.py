"""Tests for the optional OpenAI Agents SDK adapter."""

import asyncio

import pytest

pytest.importorskip("agents")

from agents import Agent, function_tool

from pikit.adapters import TaintRouter
from pikit.adapters.openai_agents import OpenAIAgentsAdapter
from pikit.agent import DefenseHooks
from pikit.defenses import get


@function_tool
def fetch_url(url: str) -> str:
    """Fetch a URL."""
    return "clean page"


class _Result:
    final_output = "Agent saw the tool result."


async def _fake_run(agent, message, **kwargs):
    tool = agent.tools[0]
    await tool.on_invoke_tool(None, '{"url": "https://example.test/report"}')
    return _Result()


def test_openai_agents_adapter_wraps_tainted_function_tool(monkeypatch):
    import agents

    monkeypatch.setattr(agents.Runner, "run", _fake_run)
    adapter = OpenAIAgentsAdapter(
        Agent(name="test", instructions="Use tools safely.", tools=[fetch_url]),
        taint_router=TaintRouter(taint={"fetch_url": "TAINTED PAGE"}),
    )
    trace = asyncio.run(adapter.arun("Fetch the report"))

    assert trace.final_text == "Agent saw the tool result."
    assert trace.tainted_steps[0].tool_name == "fetch_url"
    assert trace.tainted_steps[0].content == "TAINTED PAGE"


def test_openai_agents_adapter_applies_tool_result_defense(monkeypatch):
    import agents

    monkeypatch.setattr(agents.Runner, "run", _fake_run)
    adapter = OpenAIAgentsAdapter(
        Agent(name="test", tools=[fetch_url]),
        taint_router=TaintRouter(taint={"fetch_url": "TAINTED PAGE"}),
        defenses=DefenseHooks(tool_result=get("delimiters")()),
        sink_tools={"fetch_url"},
    )
    trace = asyncio.run(adapter.arun("Fetch the report"))

    assert "<data>" in trace.tainted_steps[0].content
    assert trace.sink_calls[0].tool_name == "fetch_url"


def test_openai_agents_adapter_sync_run_rejects_active_loop(monkeypatch):
    import agents

    monkeypatch.setattr(agents.Runner, "run", _fake_run)
    adapter = OpenAIAgentsAdapter(Agent(name="test", tools=[fetch_url]))

    async def invoke_sync_api():
        with pytest.raises(RuntimeError, match="active event loop"):
            adapter.run("Fetch the report")

    asyncio.run(invoke_sync_api())
