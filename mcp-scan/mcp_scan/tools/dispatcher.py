# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

import inspect
from typing import TYPE_CHECKING, Any, Optional

from mcp_scan.tools.registry import get_tool_by_name, get_tools_prompt, needs_context
from mcp_scan.utils import strip_surrogates
from mcp_scan.utils.loging import logger
from mcp_scan.utils.mcp_tools import MCPTools
from mcp_scan.utils.prompt_manager import prompt_manager

if TYPE_CHECKING:  # pragma: no cover
    from mcp_scan.utils.tool_context import ToolContext

# 动态扫描模式下的安全工具白名单：仅允许只读/元信息工具，禁止 execute_shell / read_file
# 等本地操作工具，防止恶意 MCP 工具描述中的 prompt injection 诱导 agent 执行任意命令。
_DYNAMIC_SAFE_TOOLS = frozenset({
    "finish",
    "think",
    "call_mcp_tool",
    "list_mcp_tools",
    "list_mcp_prompts",
    "list_mcp_resources",
})


class ToolDispatcher:
    def __init__(
        self, mcp_server_url: str | None = None, mcp_headers: dict[str, str] | None = None
    ):
        """
        NOTE: __init__ must be synchronous. We do lazy MCP connection on first remote usage.
        """
        self.mcp_server_url = mcp_server_url
        self.mcp_tools_manager: MCPTools | None = None
        self.mcp_transport = None
        self.mcp_headers = mcp_headers

    async def _ensure_mcp_manager(self) -> MCPTools | None:
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
                logger.info(
                    f"ToolDispatcher: MCP tools manager initialized with transport: {transport}"
                )
                return self.mcp_tools_manager
            except Exception as e:
                logger.warning(
                    f"ToolDispatcher: transport '{transport}' failed for {self.mcp_server_url}: {type(e).__name__}: {e}"
                )
                continue

        logger.error(f"ToolDispatcher: Failed to connect to MCP server: {self.mcp_server_url}")
        return None

    async def get_all_tools_prompt(self) -> str:
        """获取所有可用工具的描述 Prompt

        动态扫描模式（mcp_server_url 非空）下仅暴露安全工具子集，
        防止恶意 MCP 工具描述中的 prompt injection 诱导 agent 调用
        execute_shell 等危险本地工具。
        """
        if self.mcp_server_url:
            # 动态扫描：仅注册安全工具，移除 execute_shell / read_file
            prompt = get_tools_prompt(list(_DYNAMIC_SAFE_TOOLS))
            manager = await self._ensure_mcp_manager()
            if not manager:
                raise RuntimeError("Failed to connect to MCP server")
            try:
                mcp_prompt = await manager.describe_mcp_tools()
                mcp_remote_prompt = prompt_manager.format_prompt(
                    "dynamic/system_prompt", mcp_tools=mcp_prompt
                )
                prompt += f"\n\n{mcp_remote_prompt}"
            except Exception as e:
                logger.error(f"Failed to fetch MCP tools description: {e}")
                return prompt
        else:
            # 静态扫描：全部工具可用
            prompt = get_tools_prompt([])

        return prompt

    async def call_tool(
        self, tool_name: str, args: dict[str, Any], context: Optional["ToolContext"] = None
    ) -> str:
        """统一调用入口：自动识别是本地还是远程工具"""
        # 动态扫描模式下的工具白名单拦截：
        # 防止恶意 MCP 工具描述中的 prompt injection 诱导 agent 调用
        # execute_shell / read_file 等危险本地工具。
        if self.mcp_server_url and tool_name not in _DYNAMIC_SAFE_TOOLS:
            logger.warning(
                f"Blocked tool '{tool_name}' in dynamic scan mode — not in safe whitelist"
            )
            return (
                f"Error: Tool '{tool_name}' is not available in dynamic scan mode. "
                f"Only MCP interaction tools are allowed."
            )

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
            return strip_surrogates(ret)
        return strip_surrogates(str(result))

    async def close(self):
        if self.mcp_tools_manager:
            await self.mcp_tools_manager.close()
            logger.info("ToolDispatcher: MCP tools manager closed")
