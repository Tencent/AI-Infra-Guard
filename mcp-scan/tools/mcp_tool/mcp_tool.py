from typing import Any, Optional

from utils.tool_context import ToolContext
from tools.registry import register_tool


@register_tool(sandbox_execution=False)
async def mcp_tool(tool_name: str, context: ToolContext = None, **kwargs) -> dict[str, Any]:
    print(f"mcp_tool: {tool_name}, {context}, {kwargs}")
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


@register_tool(sandbox_execution=False)
async def mcp_resource(
        resource_name: Optional[str] = None,
        uri: Optional[str] = None,
        context: ToolContext = None,
) -> dict[str, Any]:
    """
    读取远程 MCP 服务器暴露的资源内容。

    - 可以通过 `resource_name`（资源名称）读取，内部会自动解析为 URI（基于资源列表缓存）
    - 也可以直接通过 `uri` 读取指定资源
    """
    print(f"mcp_resource: resource_name={resource_name}, uri={uri}, context={context}")
    if not context:
        return {"error": "ToolContext is required for mcp_resource"}

    if not resource_name and not uri:
        return {"error": "Either resource_name or uri must be provided for mcp_resource"}

    try:
        content = await context.read_mcp_resource(resource_name=resource_name, uri=uri)
    except Exception as e:
        return {
            "error": str(e)
        }

    return {
        "resource_name": resource_name,
        "uri": uri,
        "content": content,
    }
