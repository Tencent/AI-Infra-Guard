import inspect
import copy
from typing import Any, Dict, Optional, TYPE_CHECKING
from tools.registry import get_tool_by_name, needs_context
from utils.mcp_tools import MCPTools
from utils.loging import logger
from utils.prompt_manager import prompt_manager
from tools.registry import get_tools_prompt

if TYPE_CHECKING:  # pragma: no cover
    from utils.tool_context import ToolContext


class ToolDispatcher:
    def __init__(self, ):
        """
        NOTE: __init__ must be synchronous. We do lazy MCP connection on first remote usage.
        """

    async def get_all_tools_prompt(self) -> str:
        return get_tools_prompt([])

    async def call_tool(self, tool_name: str, args: Dict[str, Any], context: Optional["ToolContext"] = None) -> str:
        """统一调用入口：自动识别是本地还是远程工具"""
        # 1. 尝试作为本地工具调用
        tool_func = get_tool_by_name(tool_name)
        if tool_func:
            if needs_context(tool_name) and context:
                args["context"] = context
            try:
                result = tool_func(**args)
            except Exception as e:
                return f"Error: {e}"
            if inspect.isawaitable(result):
                result = await result
            return self._format_result(result)
        return f"Error: Tool '{tool_name}' not found locally or MCP server is unavailable"

    def _format_result(self, result: Any) -> str:
        if isinstance(result, dict):
            ret = ""
            for k, v in result.items():
                ret += f"<{k}>{v}</{k}>\n"
            return ret
        return str(result)
