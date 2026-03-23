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

import subprocess
import time
import os
import signal
import tempfile
from typing import Any, Optional
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext

@register_tool
def execute_shell(command: str, timeout: int = 30, cwd: Optional[str] = None) -> dict[str, Any]:
    """执行 Shell 命令
    
    Args:
        command: 要执行的 Shell 命令
        timeout: 超时时间（秒），默认 30 秒
        cwd: 执行命令的工作目录（可选）
        
    Returns:
        包含执行结果的字典
    """
    try:
        # 确保 timeout 是数字，防止 float + str 错误 (subprocess 内部会进行 time.time() + timeout)
        try:
            timeout = float(timeout) if timeout else 60*60*6
        except Exception as e:
            timeout = 60*60*6
        
        result = subprocess.run(
            str(command),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )

        output = {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
        return output

    except subprocess.TimeoutExpired:
        logger.error(f"Shell command timeout after {timeout}s")
        return {
            "success": False,
            "message": f"Execution timeout after {timeout} seconds",
            "stdout": "",
            "stderr": "Timeout",
            "return_code": -1
        }
    except Exception as e:
        logger.error(f"Error executing shell command: {e}")
        return {
            "success": False,
            "message": f"Error executing shell command: {str(e)}",
            "stdout": "",
            "stderr": str(e),
            "return_code": -1
        }
