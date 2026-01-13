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
    def __init__(self, mcp_server_url: Optional[str] = None, mcp_headers: Optional[Dict[str, str]] = None):
        """
        NOTE: __init__ must be synchronous. We do lazy MCP connection on first remote usage.
        """
        self.mcp_server_url = mcp_server_url
        self.mcp_tools_manager: Optional[MCPTools] = None
        self.mcp_transport = None
        self.mcp_headers = mcp_headers

    async def _ensure_mcp_manager(self) -> Optional[MCPTools]:
        if not self.mcp_server_url:
            return None
        if self.mcp_tools_manager:
            return self.mcp_tools_manager

        transports = [self.mcp_transport] if self.mcp_transport else ["streamable-http", "sse"]
        for transport in transports:
            if not transport:
                continue
            try:
                manager = MCPTools(self.mcp_server_url, transport, headers=self.mcp_headers)  # type: ignore[arg-type]
                # verify connectivity
                await manager.describe_mcp_tools()
                self.mcp_tools_manager = manager
                logger.info(f"ToolDispatcher: MCP tools manager initialized with transport: {transport}")
                return self.mcp_tools_manager
            except Exception:
                continue

        logger.error(f"ToolDispatcher: Failed to connect to MCP server: {self.mcp_server_url}")
        return None

    async def get_all_tools_prompt(self) -> str:
        """获取所有可用工具的描述 Prompt"""
        common_tools = ['finish', 'think']

        normal_tools = copy.copy(common_tools)
        normal_tools.extend(['read_file', 'execute_shell'])

        dynamic_tools = copy.copy(common_tools)
        dynamic_tools.extend(['mcp_tool'])

        if self.mcp_server_url:
            prompt = get_tools_prompt(dynamic_tools or [])
            manager = await self._ensure_mcp_manager()
            if not manager:
                raise RuntimeError("Failed to connect to MCP server")
            try:
                mcp_prompt = await manager.describe_mcp_tools()
                mcp_remote_prompt = prompt_manager.format_prompt("dynamic/system_prompt", mcp_tools=mcp_prompt)
                prompt += f"\n\n{mcp_remote_prompt}"
            except Exception as e:
                logger.error(f"Failed to fetch MCP tools description: {e}")
                return prompt
        else:
            prompt = get_tools_prompt(normal_tools or [])

        return prompt

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

    async def close(self):
        if self.mcp_tools_manager:
            await self.mcp_tools_manager.close()
            logger.info("ToolDispatcher: MCP tools manager closed")
