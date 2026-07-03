import os
from typing import Any

from skill_scan.tools.registry import register_tool
from skill_scan.utils.loging import logger
from skill_scan.utils.tool_context import ToolContext


# @register_tool
def write_file(file_path: str, content: str, context: ToolContext = None) -> dict[str, Any]:
    """Write content to a file (overwrites existing files).

    Args:
        file_path: File path
        content: Content to write

    Returns:
        Dict containing success status and message
    """
    try:
        # Create the directory if it does not exist
        directory = os.path.dirname(file_path)
        if not directory.startswith(context.folder):
            return {
                "success": False,
                "message": f"Path is not allowed: {file_path}"
            }
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Wrote file: {file_path} ({len(content)} chars)")

        return {
            "success": True,
            "message": f"Successfully wrote {len(content)} characters to {file_path}",
        }

    except PermissionError:
        return {
            "success": False,
            "message": f"Permission denied: {file_path}",
        }
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        return {
            "success": False,
            "message": f"Error writing file: {str(e)}",
        }
