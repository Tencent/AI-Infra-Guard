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

"""Directory listing tool constrained to the target agent repository."""

import os
from typing import Any

from agent_scan.tools.file._common import format_size, resolve_repo_target
from agent_scan.tools.registry import register_tool
from agent_scan.utils.logging import logger
from agent_scan.utils.path_utils import IGNORE_DIRECTORIES, is_path_within, relative_path
from agent_scan.utils.tool_context import ToolContext


@register_tool
def ls(path: str = ".", context: ToolContext = None) -> dict[str, Any]:
    """List files and subdirectories directly under a directory in the target repository."""
    resolved, root, err = resolve_repo_target(path, context, allow_empty_as_root=True)
    if err or not resolved or not root:
        return {"success": False, "message": err or f"Invalid path: {path}"}

    if not os.path.isdir(resolved):
        return {"success": False, "message": f"Path is not a directory: {path}"}

    entries: list[str] = []
    try:
        names = sorted(os.listdir(resolved))
    except OSError as exc:
        return {"success": False, "message": f"Failed to list directory: {exc}"}

    for name in names:
        full = os.path.join(resolved, name)
        if not is_path_within(full, root):
            continue
        is_dir = os.path.isdir(full)
        if is_dir and name in IGNORE_DIRECTORIES:
            continue
        entry_type = "dir" if is_dir else "file"
        size_text = ""
        if entry_type == "file":
            try:
                size_text = format_size(os.path.getsize(full))
            except OSError:
                size_text = "0 B"
        entries.append(f"[{entry_type}] {name}" + (f"  ({size_text})" if size_text else ""))

    rel = relative_path(resolved, root)
    logger.info(f"ls: {rel} -> {len(entries)} entries")
    return {
        "success": True,
        "path": rel,
        "count": len(entries),
        "entries": "\n".join(entries),
    }
