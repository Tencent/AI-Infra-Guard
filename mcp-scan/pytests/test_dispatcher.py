import pytest

from mcp_scan.tools.dispatcher import ToolDispatcher


@pytest.mark.asyncio
async def test_ensure_mcp_manager_records_underlying_connection_error(monkeypatch):
    """When every transport attempt fails, the dispatcher must retain the actual underlying
    error, not silently discard it.

    Reproduces #534: a user whose MCP server is reachable (curl succeeds) still gets a bare
    "Failed to connect to MCP server" with no indication of what actually failed, because
    every per-transport exception was discarded by `except Exception: continue`.
    """

    async def fake_describe_mcp_tools(self):
        raise RuntimeError("Failed to fetch MCP tools: ConnectionRefusedError: [Errno 111] Connection refused")

    monkeypatch.setattr(
        "mcp_scan.tools.dispatcher.MCPTools.describe_mcp_tools", fake_describe_mcp_tools
    )

    dispatcher = ToolDispatcher(mcp_server_url="http://example.invalid/mcp")
    manager = await dispatcher._ensure_mcp_manager()

    assert manager is None
    assert dispatcher.last_connect_error is not None
    assert "ConnectionRefusedError" in str(dispatcher.last_connect_error)


@pytest.mark.asyncio
async def test_get_all_tools_prompt_raises_with_underlying_error_detail(monkeypatch):
    """The RuntimeError raised to callers of get_all_tools_prompt() must include the
    underlying connection failure detail, not just the generic "Failed to connect" string."""

    async def fake_describe_mcp_tools(self):
        raise RuntimeError("Failed to fetch MCP tools: ConnectionRefusedError: [Errno 111] Connection refused")

    monkeypatch.setattr(
        "mcp_scan.tools.dispatcher.MCPTools.describe_mcp_tools", fake_describe_mcp_tools
    )

    dispatcher = ToolDispatcher(mcp_server_url="http://example.invalid/mcp")
    with pytest.raises(RuntimeError, match="ConnectionRefusedError"):
        await dispatcher.get_all_tools_prompt()
