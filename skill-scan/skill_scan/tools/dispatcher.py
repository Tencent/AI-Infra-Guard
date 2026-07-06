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
from typing import Any, Dict, Optional, TYPE_CHECKING

from skill_scan.tools.registry import get_tool_by_name, get_tools_prompt, needs_context
from skill_scan.utils.loging import logger

if TYPE_CHECKING:
    from skill_scan.utils.tool_context import ToolContext

# Tool set dedicated to aig-skill-scan
_SKILL_TOOLS = [
    "finish",
    "think",
    "read_file",
    "ls",
    "grep",
    "dir_tree",
    "base64_decode",
]


class ToolDispatcher:
    """Tool dispatcher for aig-skill-scan.

    aig-skill-scan only uses local tools and does not make remote MCP calls.
    """

    async def get_all_tools_prompt(self) -> str:
        """Get the description prompt for all available tools."""
        return get_tools_prompt(_SKILL_TOOLS)

    async def call_tool(
        self, tool_name: str, args: Dict[str, Any], context: Optional["ToolContext"] = None
    ) -> str:
        """Unified call entry point."""
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
        return f"Error: Tool '{tool_name}' not found"

    def _format_result(self, result: Any) -> str:
        if isinstance(result, dict):
            ret = ""
            for k, v in result.items():
                if isinstance(v, list):
                    items = "\n".join(str(i) for i in v)
                    ret += f"<{k}>\n{items}\n</{k}>\n"
                else:
                    ret += f"<{k}>{v}</{k}>\n"
            return ret
        return str(result)

    async def close(self):
        pass
