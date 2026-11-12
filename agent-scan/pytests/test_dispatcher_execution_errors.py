"""Local tool failures should be observations, while cancellation propagates."""

import asyncio

import pytest

from agent_scan.tools import registry
from agent_scan.tools.dispatcher import ToolDispatcher


@pytest.fixture
def isolated_registry(monkeypatch):
    """Register real test tools without leaking them into other tests."""
    monkeypatch.setattr(registry, "tools", list(registry.tools))
    monkeypatch.setattr(registry, "_tools_by_name", dict(registry._tools_by_name))


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["sync", "async", "wrapper"])
@pytest.mark.parametrize("error_type", [ValueError, TypeError])
async def test_tool_execution_errors_are_returned(isolated_registry, kind, error_type):
    def sync_tool():
        raise error_type("deliberate tool failure")

    async def async_tool():
        raise error_type("deliberate tool failure")

    def wrapper():
        return async_tool()

    callback = {"sync": sync_tool, "async": async_tool, "wrapper": wrapper}[kind]
    registry.register_tool(callback)
    result = await ToolDispatcher().call_tool(callback.__name__, {})
    assert result.startswith("Error:")
    assert "deliberate tool failure" in result


@pytest.mark.asyncio
@pytest.mark.parametrize("is_async", [False, True])
async def test_successful_tool_result_is_preserved(isolated_registry, is_async):
    def sync_tool():
        return {"success": True, "output": "completed"}

    async def async_tool():
        return sync_tool()

    callback = async_tool if is_async else sync_tool
    registry.register_tool(callback)
    result = await ToolDispatcher().call_tool(callback.__name__, {})
    assert result == "<success>True</success>\n<output>completed</output>\n"


@pytest.mark.asyncio
async def test_tool_cancellation_still_propagates(isolated_registry):
    async def cancelled_tool():
        raise asyncio.CancelledError("stop scan")

    registry.register_tool(cancelled_tool)
    with pytest.raises(asyncio.CancelledError, match="stop scan"):
        await ToolDispatcher().call_tool("cancelled_tool", {})
