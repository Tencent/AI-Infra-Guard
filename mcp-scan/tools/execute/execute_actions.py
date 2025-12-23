import subprocess
import signal
import os
import time
from typing import Any, Optional

from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext


def _execute_code(code: str, timeout: int) -> dict[str, Any]:
    """执行Python代码的辅助函数
    
    Args:
        code: 要执行的Python代码
        timeout: 超时时间
        
    Returns:
        执行结果字典
    """
    import tempfile

    # 创建临时文件
    temp_file = None
    try:
        # 创建临时 Python 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name

        logger.debug(f"Executing Python code from temporary file: {temp_file}")

        # 执行临时文件
        result = subprocess.run(
            ["python3", temp_file],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        output = {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "temp_file": temp_file  # 返回临时文件路径，便于调试
        }

        # 如果执行失败，在 stderr 中添加临时文件信息
        if result.returncode != 0:
            output["message"] = f"Python code execution failed. Temp file: {temp_file}"
            logger.error(f"Python execution failed, temp file kept at: {temp_file}")
        else:
            # 成功时删除临时文件
            try:
                os.remove(temp_file)
                output["temp_file"] = None
            except:
                pass

        return output

    except subprocess.TimeoutExpired:
        logger.error(f"Python code execution timeout after {timeout}s")
        error_msg = f"Execution timeout after {timeout} seconds. Temp file: {temp_file}"
        return {
            "success": False,
            "message": error_msg,
            "stdout": "",
            "stderr": error_msg,
            "return_code": -1,
            "temp_file": temp_file
        }
    except Exception as e:
        logger.error(f"Error executing Python code: {e}")
        error_msg = f"Error executing Python code: {str(e)}"
        if temp_file:
            error_msg += f"\nTemp file: {temp_file}"
        return {
            "success": False,
            "message": error_msg,
            "stdout": "",
            "stderr": str(e),
            "return_code": -1,
            "temp_file": temp_file
        }


@register_tool
def execute_shell(command: str, timeout: int = 300) -> dict[str, Any]:
    """执行 Shell 命令
    
    Args:
        command: 要执行的 Shell 命令
        timeout: 超时时间（秒），默认 300 秒
        
    Returns:
        包含执行结果的字典
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
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
