from typing import Any, Optional, Literal
from utils.mcp_tools import MCPTools
from tools.registry import register_tool
from utils.tool_context import ToolContext


async def _get_mcp_manager(url: Optional[str], transport: str, context: Optional[ToolContext]) -> MCPTools:
    """Helper to get MCPTools manager, either from context or creating a new one."""
    if url:
        return MCPTools(url=url, transport=transport) # type: ignore
    
    if context and context.tool_dispatcher and context.tool_dispatcher.mcp_server_url:
        manager = await context.tool_dispatcher._ensure_mcp_manager()
        if manager:
            return manager
            
    raise ValueError("MCP server URL is required (either via parameter or global configuration)")


@register_tool(sandbox_execution=False)
async def call_mcp_tool(
    tool_name: str, 
    url: Optional[str] = None, 
    transport: Literal["sse", "streamable-http"] = "sse",
    context: Optional[ToolContext] = None, 
    **kwargs
) -> dict[str, Any]:
    """Call a remote MCP server tool."""
    try:
        manager = await _get_mcp_manager(url, transport, context)
        ret = await manager.call_remote_tool(tool_name, **kwargs)
        return {
            "tool_name": tool_name,
            "tool_result": ret
        }
    except Exception as e:
        return {"error": str(e)}


@register_tool(sandbox_execution=False)
async def list_mcp_tools(
    url: Optional[str] = None, 
    transport: Literal["sse", "streamable-http"] = "sse",
    context: Optional[ToolContext] = None
) -> dict[str, Any]:
    """List tools available on a remote MCP server."""
    try:
        manager = await _get_mcp_manager(url, transport, context)
        ret = await manager.describe_mcp_tools()
        return {"tools": ret}
    except Exception as e:
        return {"error": str(e)}


@register_tool(sandbox_execution=False)
async def list_mcp_prompts(
    url: Optional[str] = None, 
    transport: Literal["sse", "streamable-http"] = "sse",
    context: Optional[ToolContext] = None
) -> dict[str, Any]:
    """List prompts available on a remote MCP server."""
    try:
        manager = await _get_mcp_manager(url, transport, context)
        ret = await manager.list_remote_prompts()
        return {"prompts": ret}
    except Exception as e:
        return {"error": str(e)}


@register_tool(sandbox_execution=False)
async def list_mcp_resources(
    url: Optional[str] = None, 
    transport: Literal["sse", "streamable-http"] = "sse",
    context: Optional[ToolContext] = None
) -> dict[str, Any]:
    """List resources available on a remote MCP server."""
    try:
        manager = await _get_mcp_manager(url, transport, context)
        ret = await manager.list_remote_resources()
        return {"resources": ret}
    except Exception as e:
        return {"error": str(e)}


# Alias for backward compatibility
# mcp_tool = call_mcp_tool
