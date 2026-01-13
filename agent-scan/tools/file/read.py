"""
Read 工具 - 读取文件内容
实现 offset/limit、50KB 字节预算、行号输出以及对图片/PDF 的附件返回
"""
import os
import base64
import mimetypes
from typing import Any, Optional, List
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext
from utils.path_utils import validate_path
from utils.file_utils import (
    is_binary_file, is_image_file, is_pdf_file,
    read_file_with_lines, safe_read_file
)


DEFAULT_READ_LIMIT = 2000
MAX_BYTES = 50 * 1024  # 50KB
MAX_LINE_LENGTH = 2000


@register_tool
def read(
    file_path: str,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
    context: ToolContext = None
) -> dict[str, Any]:
    """
    读取文件内容
    
    Args:
        file_path: 文件路径
        offset: 起始行号（0-based）
        limit: 读取的行数（默认 2000）
        context: 工具上下文
        
    Returns:
        包含文件内容的字典
    """
    try:
        # 解析和验证路径
        root = context.folder if context else os.getcwd()
        is_valid, resolved_path, error = validate_path(file_path, root, must_exist=True)
        
        if not is_valid:
            # 尝试提供建议
            if "does not exist" in (error or ""):
                dir_path = os.path.dirname(resolved_path)
                base_name = os.path.basename(resolved_path)
                
                if os.path.isdir(dir_path):
                    try:
                        entries = os.listdir(dir_path)
                        suggestions = [
                            e for e in entries
                            if base_name.lower() in e.lower() or e.lower() in base_name.lower()
                        ][:3]
                        
                        if suggestions:
                            suggestion_paths = [os.path.join(dir_path, s) for s in suggestions]
                            error = f"{error}\n\nDid you mean one of these?\n" + '\n'.join(suggestion_paths)
                    except OSError:
                        pass
            
            return {
                "success": False,
                "error": error
            }
        
        if os.path.isdir(resolved_path):
            return {
                "success": False,
                "error": f"Path is a directory, not a file: {resolved_path}"
            }
        
        # 获取文件标题
        title = os.path.relpath(resolved_path, root)
        
        # 处理图片文件
        if is_image_file(resolved_path):
            mime_type = mimetypes.guess_type(resolved_path)[0] or 'image/png'
            
            with open(resolved_path, 'rb') as f:
                content = f.read()
            
            base64_data = base64.b64encode(content).decode('utf-8')
            
            return {
                "success": True,
                "title": title,
                "output": "Image read successfully",
                "truncated": False,
                "attachment": {
                    "type": "file",
                    "mime": mime_type,
                    "data": base64_data
                }
            }
        
        # 处理 PDF 文件
        if is_pdf_file(resolved_path):
            with open(resolved_path, 'rb') as f:
                content = f.read()
            
            base64_data = base64.b64encode(content).decode('utf-8')
            
            return {
                "success": True,
                "title": title,
                "output": "PDF read successfully",
                "truncated": False,
                "attachment": {
                    "type": "file",
                    "mime": "application/pdf",
                    "data": base64_data
                }
            }
        
        # 检查二进制文件
        if is_binary_file(resolved_path):
            return {
                "success": False,
                "error": f"Cannot read binary file: {resolved_path}"
            }
        
        # 读取文本文件
        read_offset = offset or 0
        read_limit = limit or DEFAULT_READ_LIMIT
        
        lines, total_lines, has_more, truncated_by_bytes = read_file_with_lines(
            resolved_path,
            offset=read_offset,
            limit=read_limit,
            max_bytes=MAX_BYTES,
            max_line_length=MAX_LINE_LENGTH
        )
        
        # 构建输出
        output = "<file>\n"
        output += '\n'.join(lines)
        
        last_read_line = read_offset + len(lines)
        truncated = has_more or truncated_by_bytes
        
        if truncated_by_bytes:
            output += f"\n\n(Output truncated at {MAX_BYTES} bytes. Use 'offset' parameter to read beyond line {last_read_line})"
        elif has_more:
            output += f"\n\n(File has more lines. Use 'offset' parameter to read beyond line {last_read_line})"
        else:
            output += f"\n\n(End of file - total {total_lines} lines)"
        
        output += "\n</file>"
        
        # 预览内容（前 20 行）
        preview = '\n'.join(lines[:20]) if lines else ""
        
        logger.info(f"Read file: {resolved_path} (lines {read_offset+1}-{last_read_line} of {total_lines})")
        
        return {
            "success": True,
            "title": title,
            "output": output,
            "preview": preview,
            "truncated": truncated,
            "total_lines": total_lines,
            "lines_read": len(lines)
        }
        
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return {
            "success": False,
            "error": f"Error reading file: {str(e)}"
        }

