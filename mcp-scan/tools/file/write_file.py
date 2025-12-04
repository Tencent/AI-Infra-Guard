import os
import difflib
from typing import Any
from tools.registry import register_tool
from utils.loging import logger
from utils.tool_context import ToolContext

@register_tool
def write_file(file_path: str, content: str, context: ToolContext = None) -> dict[str, Any]:
    """
    Writes content to a file.
    Supports automatic creation of directories.
    Returns a diff of the changes.

    Args:
        file_path: The path to the file to write.
        content: The content to write.
        context: Optional tool context.

    Returns:
        A dictionary indicating success and showing the diff.
    """
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        # Read original content for diff
        original_content = ""
        file_exists = False
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                file_exists = True
            except UnicodeDecodeError:
                return {
                    "error": "Cannot write to binary file",
                    "success": False
                }

        # Write new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Generate Diff
        diff = difflib.unified_diff(
            original_content.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"a/{file_path}" if file_exists else "/dev/null",
            tofile=f"b/{file_path}",
            lineterm=""
        )
        diff_text = "".join(diff)

        status_msg = f"Successfully wrote to {file_path}"
        if not file_exists:
            status_msg = f"Created new file {file_path}"

        return {
            "success": True,
            "message": status_msg,
            "diff": diff_text,
            "file_path": file_path
        }

    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        return {
            "error": str(e),
            "success": False
        }
