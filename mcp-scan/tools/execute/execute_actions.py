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
