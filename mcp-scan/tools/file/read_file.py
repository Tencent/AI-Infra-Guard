import os
import mimetypes
import logging
from typing import Any, Optional

from tools.registry import register_tool
from utils.loging import logger

@register_tool
def read_file(file_path: str, offset: int = 0, limit: int = -1) -> dict[str, Any]:
    """
    Reads a file from the filesystem.
    Supports reading a specific range of lines using offset and limit.
    Automatically handles text and binary files (returns base64 for binary).

    Args:
        file_path: The path to the file to read.
        offset: (Optional) The line number to start reading from (0-based).
        limit: (Optional) The number of lines to read. -1 for all.

    Returns:
        A dictionary containing the file content or error message.
    """
    try:
        if not os.path.exists(file_path):
            return {
                "error": f"File not found: {file_path}",
                "success": False
            }

        if os.path.isdir(file_path):
            return {
                "error": f"Path is a directory: {file_path}",
                "success": False
            }

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 20:
            return {
                "error": f"File too large ({file_size_mb:.2f}MB). Limit is 20MB.",
                "success": False
            }

        mime_type, _ = mimetypes.guess_type(file_path)
        is_text = True

        # Simple check for binary content if mime_type is not obvious
        if mime_type and not mime_type.startswith('text'):
             # Read first chunk to check for null bytes
             with open(file_path, 'rb') as f:
                 chunk = f.read(1024)
                 if b'\0' in chunk:
                     is_text = False

        if is_text:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                total_lines = len(lines)

                # Apply offset and limit
                start_index = max(0, offset)
                end_index = total_lines
                if limit > 0:
                    end_index = min(start_index + limit, total_lines)

                selected_lines = lines[start_index:end_index]
                content = "".join(selected_lines)

                is_truncated = (start_index > 0) or (end_index < total_lines)

                display_msg = f"Read {len(selected_lines)} lines from {file_path}"
                if is_truncated:
                    display_msg += f" (lines {start_index+1}-{end_index} of {total_lines})"

                    # Add truncation warning to content for LLM
                    content = f"--- FILE CONTENT (lines {start_index+1}-{end_index} of {total_lines}) ---\n{content}\n--- (Truncated) Use offset/limit to read more ---"

                return {
                    "content": content,
                    "success": True,
                    "message": display_msg,
                    "mime_type": mime_type or 'text/plain',
                    "total_lines": total_lines
                }
            except UnicodeDecodeError:
                # Fallback to binary handling if text decode fails
                is_text = False

        if not is_text:
             import base64
             with open(file_path, 'rb') as f:
                 data = f.read()
                 encoded = base64.b64encode(data).decode('utf-8')
                 return {
                     "content": f"<binary_file path='{file_path}' size='{len(data)} bytes' />", # Don't dump base64 to LLM context usually
                     "base64_data": encoded,
                     "success": True,
                     "message": f"Read binary file {file_path} ({len(data)} bytes)",
                     "is_binary": True
                 }

    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return {
            "error": str(e),
            "success": False
        }
