"""
Write 工具 - 写入/创建文件
必要时创建父目录，并返回 Diff 与基础诊断信息
"""
import os
from typing import Any, Optional
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext
from utils.path_utils import validate_path, ensure_parent_dir, is_path_within
from utils.file_utils import (
    generate_unified_diff, trim_diff_indentation,
    safe_read_file, safe_write_file
)


@register_tool
def write(
    file_path: str,
    content: str,
    context: ToolContext = None
) -> dict[str, Any]:
    """
    写入文件内容
    
    Args:
        file_path: 文件路径
        content: 要写入的内容
        context: 工具上下文
        
    Returns:
        包含执行结果的字典
    """
    try:
        # 解析和验证路径
        root = context.folder if context else os.getcwd()
        is_valid, resolved_path, error = validate_path(file_path, root)
        
        if not is_valid:
            return {
                "success": False,
                "error": error
            }
        
        # 检查是否为目录
        if os.path.isdir(resolved_path):
            return {
                "success": False,
                "error": f"Path is a directory, not a file: {resolved_path}"
            }
        
        # 获取原始内容（如果文件存在）
        exists = os.path.exists(resolved_path)
        content_old = ""
        
        if exists:
            old, err = safe_read_file(resolved_path)
            if err:
                return {
                    "success": False,
                    "error": err
                }
            content_old = old or ""
        
        # 确保父目录存在
        ensure_parent_dir(resolved_path)
        
        # 写入文件
        safe_write_file(resolved_path, content, create_dirs=True)
        
        # 生成 diff
        relative_path = os.path.relpath(resolved_path, root)
        diff = generate_unified_diff(content_old, content, relative_path)
        diff = trim_diff_indentation(diff)
        
        # 统计变更
        old_lines = content_old.split('\n') if content_old else []
        new_lines = content.split('\n')
        additions = len(new_lines)
        deletions = len(old_lines)
        
        action = "updated" if exists else "created"
        logger.info(f"File {action}: {resolved_path} (+{len(new_lines)}/-{len(old_lines)} lines)")
        
        return {
            "success": True,
            "title": relative_path,
            "diff": diff,
            "exists": exists,
            "action": action,
            "lines_written": len(new_lines),
            "output": f"File {action} successfully: {relative_path}"
        }
        
    except Exception as e:
        logger.error(f"Error writing file: {e}")
        return {
            "success": False,
            "error": f"Error writing file: {str(e)}"
        }

