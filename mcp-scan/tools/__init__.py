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

# 自动导入所有工具模块，触发 @register_tool 装饰器的执行
from tools.execute import execute_actions
from tools.file import read_file
from tools.finish import finish_actions
from tools.mcp_tool import call_mcp_tool, list_mcp_prompts, list_mcp_resources, list_mcp_tools
from tools.thinking import thinking_actions

__all__ = [
    "thinking_actions",
    "finish_actions",
    "read_file",
    "execute_actions",
    "call_mcp_tool",
    "list_mcp_tools",
    "list_mcp_prompts",
    "list_mcp_resources",
]
