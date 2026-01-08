"""
Bash 工具 - 执行 Shell 命令
"""
import subprocess
import signal
import os
from typing import Any, Optional
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext
from utils.path_utils import is_path_within, resolve_path


# 常量配置
DEFAULT_TIMEOUT = 60 * 60 * 2 # 默认超时 2 小时
MAX_OUTPUT_LENGTH = 90000  # 最大输出长度
MAX_LINES = 1000  # 最大行数


def truncate_output(output: str, max_length: int = MAX_OUTPUT_LENGTH, max_lines: int = MAX_LINES) -> str:
    """
    截断输出
    
    Args:
        output: 原始输出
        max_length: 最大字符数
        max_lines: 最大行数
        
    Returns:
        截断后的输出
    """
    lines = output.split('\n')
    
    # 先按行数截断
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        output = '\n'.join(lines) + f"\n\n... (output truncated at {max_lines} lines)"
    
    # 再按字符数截断
    if len(output) > max_length:
        output = output[:max_length] + f"\n\n... (output truncated at {max_length} characters)"
    
    return output


@register_tool
def bash(
    command: str,
    timeout: Optional[int] = None,
    workdir: Optional[str] = None,
    description: str = "",
    context: ToolContext = None
) -> dict[str, Any]:
    """
    执行 Shell 命令
    
    Args:
        command: 要执行的命令
        timeout: 超时时间（秒），默认 120 秒
        workdir: 工作目录，默认为 context.folder
        description: 命令描述（5-10 个词）
        context: 工具上下文
        
    Returns:
        包含执行结果的字典
    """
    try:
        # 解析超时
        if timeout is None:
            timeout = DEFAULT_TIMEOUT
        else:
            try:
                timeout = float(timeout)
                if timeout < 0:
                    return {
                        "success": False,
                        "error": f"Invalid timeout value: {timeout}. Timeout must be a positive number."
                    }
            except (TypeError, ValueError):
                timeout = DEFAULT_TIMEOUT
        
        # 解析工作目录
        cwd = context.folder if context else os.getcwd()
        if workdir:
            resolved_workdir = resolve_path(workdir, cwd)
            
            # 检查工作目录是否在允许范围内
            if context and context.folder:
                if not is_path_within(resolved_workdir, context.folder):
                    return {
                        "success": False,
                        "error": f"Working directory '{workdir}' is outside the allowed directory '{context.folder}'"
                    }
            
            if os.path.exists(resolved_workdir) and os.path.isdir(resolved_workdir):
                cwd = resolved_workdir
            else:
                return {
                    "success": False,
                    "error": f"Working directory does not exist or is not a directory: {resolved_workdir}"
                }
        
        logger.info(f"Executing bash command: {command[:100]}{'...' if len(command) > 100 else ''}")
        
        # 执行命令
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env={**os.environ}
        )
        
        # 合并输出
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n"
            output += result.stderr
        
        # 截断输出
        output = truncate_output(output)
        
        # 构建元数据
        metadata = []
        if result.returncode != 0:
            metadata.append(f"Command exited with code {result.returncode}")
        
        if metadata:
            output += "\n\n<bash_metadata>\n" + "\n".join(metadata) + "\n</bash_metadata>"
        
        return {
            "success": result.returncode == 0,
            "output": output,
            "exit_code": result.returncode,
            "title": description or command[:50],
        }
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out after {timeout}s: {command[:50]}")
        return {
            "success": False,
            "output": f"Command terminated after exceeding timeout {timeout}s",
            "exit_code": -1,
            "title": description or command[:50],
            "error": f"Timeout after {timeout} seconds"
        }
        
    except Exception as e:
        logger.error(f"Error executing bash command: {e}")
        return {
            "success": False,
            "output": "",
            "exit_code": -1,
            "error": f"Error executing command: {str(e)}"
        }

