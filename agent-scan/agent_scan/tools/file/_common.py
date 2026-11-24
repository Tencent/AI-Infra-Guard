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

"""Shared path and parameter validation helpers for repository inspection tools."""

from typing import Any

from agent_scan.utils.path_utils import normalize_path, validate_path
from agent_scan.utils.tool_context import ToolContext


def resolve_repo_target(
    path: str | None,
    context: ToolContext | None,
    *,
    allow_empty_as_root: bool = False,
) -> tuple[str | None, str | None, str | None]:
    """Validate context.folder and resolve a target path inside the repository root."""
    if not context or not context.folder:
        return None, None, "Repository directory (--repo) is not configured for this scan."

    raw_path = (path or "").strip()
    if not raw_path:
        if allow_empty_as_root:
            raw_path = "."
        else:
            return None, None, "Path parameter must not be empty."

    root = normalize_path(context.folder)
    is_valid, resolved, err = validate_path(raw_path, root, must_exist=True)
    if not is_valid:
        return None, root, err or f"Path is not allowed: {raw_path}"
    return resolved, root, None


def parse_positive_int(value: Any, name: str, default: int) -> tuple[int | None, str | None]:
    """Parse a positive integer argument that may arrive as a string from XML parsing."""
    if value is None or value == "":
        return default, None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, f"{name} must be an integer, got: {value!r}"
    if parsed < 1:
        return None, f"{name} must be greater than or equal to 1"
    return parsed, None


def parse_bool(value: Any, default: bool) -> bool:
    """Coerce string/bool tool arguments from XML parameters."""
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def format_size(size: int) -> str:
    """Format byte counts into a compact human-readable string."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"
