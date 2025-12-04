import subprocess
import time
import os
import signal
from typing import Any, Optional
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext


@register_tool
def execute_shell(command: str, timeout: int = 36000, background: bool = False, context: ToolContext = None) -> dict[
    str, Any]:
    """
    Executes a shell command.
    Supports both synchronous execution with timeout and background execution.

    Args:
        command: The shell command to execute.
        timeout: Timeout in seconds for synchronous execution (default: 300).
        background: If True, runs the command in background and returns PID immediately.

    Returns:
        A dictionary containing execution results (stdout, stderr, exit_code) or PID.
    """
    logger.info(f"Executing shell command: {command} (background={background})")

    try:
        if background:
            # Background execution
            # We use setsid to create a new session so it survives if the parent dies (optional but good for servers)
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
                cwd=context.repo_dir,
            )

            # Give it a moment to potentially fail immediately
            time.sleep(0.5)
            if process.poll() is not None:
                # It died immediately
                stdout, stderr = process.communicate()
                return {
                    "success": False,
                    "exit_code": process.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "message": "Command failed immediately upon start"
                }

            return {
                "success": True,
                "pid": process.pid,
                "message": f"Command started in background (PID: {process.pid})",
                "background": True
            }

        else:
            # Synchronous execution
            start_time = time.time()
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=context.repo_dir
            )
            duration = time.time() - start_time

            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
                "message": f"Command finished with code {result.returncode}"
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "timeout",
            "message": f"Command timed out after {timeout} seconds"
        }
    except Exception as e:
        logger.error(f"Shell execution error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Internal error executing command"
        }
