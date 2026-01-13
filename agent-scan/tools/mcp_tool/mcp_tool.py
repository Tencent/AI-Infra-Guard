from typing import Any

from utils.tool_context import ToolContext
from tools.registry import register_tool


@register_tool(sandbox_execution=False)
async def mcp_tool(tool_name: str, context: ToolContext = None, **kwargs) -> dict[str, Any]:
    if not context:
        return {"error": "ToolContext is required for mcp_tool"}
    try:
        ret = await context.call_mcp_tools(tool_name, kwargs)
    except Exception as e:
        return {
            "error": str(e)
        }
    return {
        "tool_name": tool_name,
        "tool_result": ret
    }
