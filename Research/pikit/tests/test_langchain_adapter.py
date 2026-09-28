"""Tests for the optional LangChain adapter."""

import pytest

pytest.importorskip("langchain_core")

from langchain.tools import tool

from pikit.adapters import TaintRouter
from pikit.adapters.langchain import LangChainAdapter
from pikit.agent import DefenseHooks
from pikit.defenses import get


@tool
def fetch_url(url: str) -> str:
    """Fetch a URL."""
    return "clean page"


class _FakeRunnable:
    """Calls the supplied wrapped tool, then returns a LangChain-like state."""

    def __init__(self, wrapped_tools):
        self._fetch = wrapped_tools[0]

    def invoke(self, inputs, **kwargs):
        content = self._fetch.invoke({"url": "https://example.test/report"})

        class Message:
            def __init__(self, value):
                self.content = value

        return {"messages": [Message("Agent saw: " + content)]}


def test_langchain_adapter_records_tainted_tool_result():
    adapter = LangChainAdapter(
        agent_factory=lambda tools: _FakeRunnable(tools),
        tools=[fetch_url],
        taint_router=TaintRouter(taint={"fetch_url": "TAINTED PAGE"}),
    )
    trace = adapter.run("Fetch the report")

    assert trace.final_text == "Agent saw: TAINTED PAGE"
    assert trace.tainted_steps[0].content == "TAINTED PAGE"
    assert trace.steps[1].kind == "tool_call"


def test_langchain_adapter_applies_tool_result_defense():
    adapter = LangChainAdapter(
        agent_factory=lambda tools: _FakeRunnable(tools),
        tools=[fetch_url],
        taint_router=TaintRouter(taint={"fetch_url": "TAINTED PAGE"}),
        defenses=DefenseHooks(tool_result=get("delimiters")()),
    )
    trace = adapter.run("Fetch the report")
    tool_result = trace.tainted_steps[0].content
    assert "<data>" in tool_result
    assert "TAINTED PAGE" in trace.final_text


def test_langchain_adapter_marks_configured_sink():
    adapter = LangChainAdapter(
        agent_factory=lambda tools: _FakeRunnable(tools),
        tools=[fetch_url],
        sink_tools={"fetch_url"},
    )
    trace = adapter.run("Fetch the report")
    assert trace.sink_calls[0].tool_name == "fetch_url"
