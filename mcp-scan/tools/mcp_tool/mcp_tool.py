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
