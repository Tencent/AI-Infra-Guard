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

from tools.registry import register_tool
from utils.logging import logger


@register_tool(sandbox_execution=False)
def finish(
        content: str,
) -> dict[str, Any]:
    """结束当前任务。
    
    参数:
    content: 简要说明完成了哪些工作内容。BaseAgent 将以此为基础，结合对话历史生成最终的格式化报告。
    """
    logger.info(f"Finish called with brief: {content}")
    return {"success": True, "message": "Task completion signaled."}