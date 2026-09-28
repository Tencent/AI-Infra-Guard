"""Tests for the optional PydanticAI adapter."""

import asyncio

import pytest

pytest.importorskip("pydantic_ai")

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from pydantic_ai.tools import Tool

from pikit.adapters import TaintRouter
from pikit.adapters.pydantic_ai import PydanticAIAdapter
from pikit.agent import DefenseHooks
from pikit.defenses import get


def fetch_url(url: str) -> str:
    """Fetch a URL."""
    return "clean page"


def test_pydantic_ai_adapter_wraps_tainted_function_tool():
    adapter = PydanticAIAdapter(
        Agent(TestModel(call_tools="all")),
        tools=[Tool(fetch_url)],
        taint_router=TaintRouter(taint={"fetch_url": "TAINTED PAGE"}),
    )
    trace = adapter.run("Fetch the report")
    assert trace.tainted_steps[0].tool_name == "fetch_url"
    assert trace.tainted_steps[0].content == "TAINTED PAGE"
    assert trace.final_text


def test_pydantic_ai_adapter_applies_tool_result_defense():
    adapter = PydanticAIAdapter(
        Agent(TestModel(call_tools="all")),
        tools=[Tool(fetch_url)],
        taint_router=TaintRouter(taint={"fetch_url": "TAINTED PAGE"}),
        sink_tools={"fetch_url"},
        defenses=DefenseHooks(tool_result=get("delimiters")()),
    )
    trace = adapter.run("Fetch the report")
    assert "<data>" in trace.tainted_steps[0].content
    assert trace.sink_calls[0].tool_name == "fetch_url"


def test_pydantic_ai_adapter_sync_run_rejects_active_loop():
    adapter = PydanticAIAdapter(Agent(TestModel()), tools=[Tool(fetch_url)])

    async def invoke_sync_api():
        with pytest.raises(RuntimeError, match="active event loop"):
            adapter.run("Fetch the report")

    asyncio.run(invoke_sync_api())
