# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

"""Bounded read-only file reader for target agent repositories."""

import os
from typing import Any

from agent_scan.tools.file._common import format_size, parse_positive_int, resolve_repo_target
from agent_scan.tools.registry import register_tool
from agent_scan.utils.file_utils import is_binary_file, read_file_with_lines
from agent_scan.utils.logging import logger
from agent_scan.utils.path_utils import relative_path
from agent_scan.utils.tool_context import ToolContext

_DEFAULT_MAX_LINES = 400
_DEFAULT_MAX_CHARS = 16000
_MAX_READ_FILE_BYTES = 10 * 1024 * 1024


@register_tool
def read_file(
    file_path: str,
    start_line: int = 1,
    max_lines: int = _DEFAULT_MAX_LINES,
    max_chars: int = _DEFAULT_MAX_CHARS,
    context: ToolContext = None,
) -> dict[str, Any]:
    """Read bounded text content with 1-based line numbers from the target repository."""
    parsed_start, err = parse_positive_int(start_line, "start_line", 1)
    if err:
        return {"success": False, "message": err}
    parsed_lines, err = parse_positive_int(max_lines, "max_lines", _DEFAULT_MAX_LINES)
    if err:
        return {"success": False, "message": err}
    parsed_chars, err = parse_positive_int(max_chars, "max_chars", _DEFAULT_MAX_CHARS)
    if err:
        return {"success": False, "message": err}

    resolved, root, err = resolve_repo_target(file_path, context, allow_empty_as_root=False)
    if err or not resolved or not root:
        return {"success": False, "message": err or f"Invalid path: {file_path}"}

    if not os.path.isfile(resolved):
        return {"success": False, "message": f"Path is not a file: {file_path}"}

    try:
        file_size = os.path.getsize(resolved)
    except OSError as exc:
        logger.error(f"read_file failed to stat {resolved}: {exc}")
        return {"success": False, "message": f"Failed to inspect file: {exc}"}

    if file_size > _MAX_READ_FILE_BYTES:
        return {
            "success": False,
            "message": (
                f"File exceeds maximum readable size ({format_size(_MAX_READ_FILE_BYTES)}): "
                f"{file_path}"
            ),
        }

    if is_binary_file(resolved):
        return {"success": False, "message": f"Binary files cannot be read as text: {file_path}"}

    try:
        lines, total_lines, has_more, truncated_by_bytes = read_file_with_lines(
            resolved,
            offset=parsed_start - 1,
            limit=parsed_lines,
            max_bytes=parsed_chars,
        )
    except OSError as exc:
        logger.error(f"read_file failed for {resolved}: {exc}")
        return {"success": False, "message": f"Failed to read file: {exc}"}

    end_line = parsed_start + len(lines) - 1 if lines else parsed_start - 1
    rel_path = relative_path(resolved, root)
    content = "\n".join(lines)
    truncated = has_more or truncated_by_bytes

    result: dict[str, Any] = {
        "success": True,
        "path": rel_path,
        "start_line": parsed_start,
        "end_line": end_line,
        "total_lines": total_lines,
        "truncated": truncated,
        "content": content,
    }
    if total_lines > 0 and parsed_start > total_lines:
        result["summary_hint"] = (
            f"Requested start_line={parsed_start} is beyond end of file (total_lines={total_lines})."
        )
    elif truncated and total_lines > 0 and end_line < total_lines:
        next_line = max(parsed_start + 1, end_line + 1)
        result["summary_hint"] = (
            f"Showing lines {parsed_start}-{end_line} of {total_lines}. "
            f"Call read_file with start_line={next_line} to continue."
        )
    return result
