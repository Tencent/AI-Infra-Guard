import os
from typing import Any

from tools.registry import register_tool
from utils.loging import logger


@register_tool
def read_file(file_path: str) -> dict[str, Any]:
    """读取文件内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        包含成功状态和文件内容的字典
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File not found: {file_path}",
            }
        
        if not os.path.isfile(file_path):
            return {
                "success": False,
                "message": f"Path is not a file: {file_path}",
            }
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        logger.info(f"Read file: {file_path} ({len(content)} chars)")
        
        return {
            "data": content
        }
        
    except UnicodeDecodeError:
        return {
            "success": False,
            "message": f"Failed to decode file {file_path}. File may be binary.",
        }
    except PermissionError:
        return {
            "success": False,
            "message": f"Permission denied: {file_path}",
        }
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return {
            "success": False,
            "message": f"Error reading file: {str(e)}",
        }





