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

"""
工具执行上下文 - 提供工具运行所需的环境信息
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:  # pragma: no cover
    from tools.dispatcher import ToolDispatcher
from utils.llm import LLM


class ToolContext:
    """工具执行上下文，包含历史记录、LLM实例等信息"""

    def __init__(
        self,
        llm: LLM,
        history: list[dict[str, str]],
        agent_name: str = "Agent",
        iteration: int = 0,
        specialized_llms: dict[str, LLM] | None = None,
        folder: str | None = None,
        tool_dispatcher: Optional["ToolDispatcher"] = None,
    ):
        """
        初始化工具上下文
        """
        self.llm = llm
        self.history = history
        self.agent_name = agent_name
        self.iteration = iteration
        self.specialized_llms = specialized_llms or {}
        self.folder = folder
        self.tool_dispatcher = tool_dispatcher

    async def call_mcp_tools(self, tool_name: str, tool_args: dict[str, Any]):
        if not self.tool_dispatcher:
            raise RuntimeError("Tool dispatcher is not available in ToolContext")
        if not self.tool_dispatcher.mcp_tools_manager:
            await self.tool_dispatcher._ensure_mcp_manager()
        if not self.tool_dispatcher.mcp_tools_manager:
            raise RuntimeError("MCP tools manager is not initialized")
        return await self.tool_dispatcher.mcp_tools_manager.call_remote_tool(tool_name, **tool_args)

    def get_llm(self, purpose: str = "default") -> LLM:
        """
        根据用途获取合适的LLM

        Args:
            purpose: LLM用途，如 "thinking", "coding", "default"

        Returns:
            LLM实例
        """
        if purpose in self.specialized_llms:
            return self.specialized_llms[purpose]
        return self.llm

    def get_recent_history(self, n: int = 5) -> list[dict[str, str]]:
        """
        获取最近的n条历史记录

        Args:
            n: 历史记录条数

        Returns:
            历史记录列表
        """
        return self.history[-n:] if len(self.history) > n else self.history

    def call_llm(
        self,
        prompt: str,
        purpose: str = "default",
        system_prompt: str | None = None,
        use_history: bool = False,
    ) -> str:
        """
        调用LLM获取响应

        Args:
            prompt: 用户提示
            purpose: LLM用途
            system_prompt: 系统提示（可选）
            use_history: 是否使用历史记录

        Returns:
            LLM响应内容
        """
        llm = self.get_llm(purpose)

        messages = []

        # 添加系统提示
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 添加历史记录（如果需要）
        if use_history:
            messages.extend(self.history[1:])

        # 添加当前提示
        messages.append({"role": "user", "content": prompt})

        return llm.chat(messages)

    def call_llm_messages(
        self,
        messages,
        purpose: str = "default",
    ) -> str:
        llm = self.get_llm(purpose)
        return llm.chat(messages)
