import subprocess
import signal
import os
import time
from typing import Any, Optional

from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext


@register_tool
def generate_python(task: str, context: ToolContext = None) -> dict[str, Any]:
    """根据需求生成 Python 代码（只生成，不执行）
    
    Args:
        task: 任务描述或需求
              例如："创建一个读取CSV的函数", "实现一个HTTP客户端", "生成数据处理脚本"
        context: 工具上下文（自动注入）
        
    Returns:
        包含生成代码的字典
    """
    if not context:
        return {
            "success": False,
            "message": "This tool requires context to access LLM"
        }
    
    logger.info(f"Generating Python code for: {task}")
    
    system_prompt = """你是一个专业的Python程序员，擅长编写高质量、简洁的代码。
你的任务是根据用户需求生成代码，要求：
1. 代码简洁、高效、可读性强
2. 遵循Python的最佳实践和编码规范
3. 包含必要的注释和文档字符串
4. 考虑边界情况和错误处理
5. 代码应该是完整的、可运行的

请直接输出可执行的Python代码，不要添加markdown代码块标记或过多解释。"""
    
    prompt = f"""请生成Python代码来实现以下需求：

{task}

请直接输出完整的、可运行的Python代码。"""
    
    try:
        generated_code = context.call_llm(
            prompt=prompt,
            purpose="coding",
            system_prompt=system_prompt,
            use_history=True
        )
        
        logger.info(f"Code generated successfully, length: {len(generated_code)} chars")
        
        return {
            "success": True,
            "generated_code": generated_code,
            "original_requirement": task,
            "message": "Code generated successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate code: {e}")
        return {
            "success": False,
            "message": f"Failed to generate code: {str(e)}",
            "error": str(e)
        }


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


@register_tool
def execute_shell_background(command: str, log_file: str = "/tmp/mcp_server.log") -> dict[str, Any]:
    """在后台执行 Shell 命令（用于长期运行的进程如服务器）
    
    Args:
        command: 要执行的 Shell 命令
        log_file: 日志文件路径，stdout和stderr会重定向到此文件
        
    Returns:
        包含进程ID和日志文件路径的字典
    """
    try:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # 打开日志文件
        with open(log_file, 'w') as log_f:
            # 启动后台进程
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                start_new_session=True  # 创建新的会话，使进程在父进程退出后继续运行
            )

        # 等待一小段时间确保进程启动
        time.sleep(0.5)

        # 检查进程是否立即失败
        poll_result = process.poll()
        if poll_result is not None:
            # 进程已经退出
            with open(log_file, 'r') as f:
                log_content = f.read()
            return {
                "success": False,
                "message": f"Process exited immediately with code {poll_result}",
                "pid": process.pid,
                "log_file": log_file,
                "log_content": log_content
            }

        logger.info(f"Background process started with PID {process.pid}, logs at {log_file}")
        return {
            "success": True,
            "message": f"Process started in background with PID {process.pid}",
            "pid": process.pid,
            "log_file": log_file
        }

    except Exception as e:
        logger.error(f"Error starting background process: {e}")
        return {
            "success": False,
            "message": f"Error starting background process: {str(e)}",
            "pid": -1,
            "log_file": log_file
        }


@register_tool
def check_process_logs(log_file: str, success_patterns: Optional[list[str]] = None,
                       error_patterns: Optional[list[str]] = None,
                       timeout: int = 60) -> dict[str, Any]:
    """检查进程日志以判断启动是否成功
    
    Args:
        log_file: 日志文件路径
        success_patterns: 成功启动的标志字符串列表（任一匹配即成功）
        error_patterns: 错误标志字符串列表（任一匹配即失败）
        timeout: 最大等待时间（秒）
        
    Returns:
        包含检查结果的字典
    """
    if success_patterns is None:
        success_patterns = [
            "started", "running", "listening", "ready",
            "server is up", "application startup complete"
        ]

    if error_patterns is None:
        error_patterns = [
            "error", "failed", "exception", "traceback",
            "address already in use", "cannot bind"
        ]

    try:
        start_time = time.time()
        last_content = ""

        while time.time() - start_time < timeout:
            if not os.path.exists(log_file):
                time.sleep(0.5)
                continue

            try:
                with open(log_file, 'r') as f:
                    content = f.read()

                if content != last_content:
                    last_content = content
                    content_lower = content.lower()

                    # 检查错误模式
                    for pattern in error_patterns:
                        if pattern.lower() in content_lower:
                            return {
                                "success": False,
                                "status": "error",
                                "message": f"Error pattern '{pattern}' found in logs",
                                "log_content": content,
                                "matched_pattern": pattern
                            }

                    # 检查成功模式
                    for pattern in success_patterns:
                        if pattern.lower() in content_lower:
                            return {
                                "success": True,
                                "status": "running",
                                "message": f"Success pattern '{pattern}' found in logs",
                                "log_content": content,
                                "matched_pattern": pattern
                            }

                time.sleep(1)

            except IOError:
                # 文件可能正在被写入，重试
                time.sleep(0.5)
                continue

        # 超时
        with open(log_file, 'r') as f:
            content = f.read() if os.path.exists(log_file) else ""

        return {
            "success": False,
            "status": "timeout",
            "message": f"Timeout after {timeout}s, no success/error pattern found",
            "log_content": content
        }

    except Exception as e:
        logger.error(f"Error checking process logs: {e}")
        return {
            "success": False,
            "status": "error",
            "message": f"Error checking logs: {str(e)}",
            "log_content": ""
        }


@register_tool
def kill_process(pid: int) -> dict[str, Any]:
    """终止指定PID的进程
    
    Args:
        pid: 要终止的进程ID
        
    Returns:
        包含终止结果的字典
    """
    if isinstance(pid, str):
        pid = int(pid)
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)

        # 检查进程是否还在运行
        try:
            os.kill(pid, 0)
            # 进程仍在运行，使用SIGKILL强制终止
            os.kill(pid, signal.SIGKILL)
            message = f"Process {pid} killed with SIGKILL"
        except ProcessLookupError:
            message = f"Process {pid} terminated with SIGTERM"

        return {
            "success": True,
            "message": message,
            "pid": pid
        }

    except ProcessLookupError:
        return {
            "success": False,
            "message": f"Process {pid} not found",
            "pid": pid
        }
    except PermissionError:
        return {
            "success": False,
            "message": f"Permission denied to kill process {pid}",
            "pid": pid
        }
    except Exception as e:
        logger.error(f"Error killing process {pid}: {e}")
        return {
            "success": False,
            "message": f"Error killing process: {str(e)}",
            "pid": pid
        }
