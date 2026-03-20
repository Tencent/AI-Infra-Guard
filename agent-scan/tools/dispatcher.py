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
import copy
from typing import Any, Dict, Optional, TYPE_CHECKING
from tools.registry import get_tool_by_name, needs_context
from utils.mcp_tools import MCPTools
from utils.logging import logger
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
