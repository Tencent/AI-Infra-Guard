from typing import Any, Dict, List, Optional
from tools.registry import get_tool_by_name, needs_context
from utils.mcp_tools import MCPTools
from utils.loging import logger
from utils.tool_context import ToolContext

class ToolDispatcher:
    def __init__(self, mcp_server_url: Optional[str] = None, mcp_transport: str = "streamable-http"):
        self.mcp_tools_manager: Optional[MCPTools] = None
        if mcp_server_url:
            self.mcp_tools_manager = MCPTools(mcp_server_url, mcp_transport)
            logger.info(f"ToolDispatcher initialized with MCP server: {mcp_server_url}")

    async def get_all_tools_prompt(self, local_tool_list: List[str] = None) -> str:
        """获取所有可用工具的描述 Prompt"""
        from tools.registry import get_tools_prompt
        prompt = get_tools_prompt(local_tool_list or [])
        
        if self.mcp_tools_manager:
            try:
                mcp_prompt = await self.mcp_tools_manager.describe_mcp_tools()
                prompt += f"\n\n{mcp_prompt}"
            except Exception as e:
                logger.error(f"Failed to fetch MCP tools description: {e}")
        
        return prompt

    async def call_tool(self, tool_name: str, args: Dict[str, Any], context: Optional[ToolContext] = None) -> str:
        """统一调用入口：自动识别是本地还是远程工具"""
        # 1. 尝试作为本地工具调用
        tool_func = get_tool_by_name(tool_name)
        if tool_func:
            if needs_context(tool_name) and context:
                args["context"] = context
            
            result = tool_func(**args)
            return self._format_result(result)

        # 2. 尝试作为远程工具调用
        if self.mcp_tools_manager:
            try:
                # 注意：mcp_tools.py 中的 call_remote_tool 返回的是 (tool_info, result)
                # 为了简化，我们只返回结果部分
                _, result = await self.mcp_tools_manager.call_remote_tool({"toolName": tool_name, "args": args})
                return str(result)
            except Exception as e:
                logger.error(f"Error calling remote tool {tool_name}: {e}")
                return f"Error: Remote tool '{tool_name}' failed: {str(e)}"

        return f"Error: Tool '{tool_name}' not found locally or on MCP server"

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

