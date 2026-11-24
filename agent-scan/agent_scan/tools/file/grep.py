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

"""Regex text search tool constrained to the target agent repository."""

import os
import re
from typing import Any

from agent_scan.tools.file._common import parse_bool, parse_positive_int, resolve_repo_target
from agent_scan.tools.registry import register_tool
from agent_scan.utils.file_utils import is_binary_file, read_text_with_fallback
from agent_scan.utils.logging import logger
from agent_scan.utils.path_utils import IGNORE_DIRECTORIES, is_path_within, relative_path
from agent_scan.utils.tool_context import ToolContext

_MAX_GREP_FILE_BYTES = 1024 * 1024


@register_tool
def grep(
    pattern: str,
    path: str = ".",
    recursive: bool = True,
    ignore_case: bool = False,
    max_results: int = 100,
    context: ToolContext = None,
) -> dict[str, Any]:
    """Search files in the target repository for lines matching a regex pattern."""
    if not pattern:
        return {"success": False, "message": "pattern must not be empty"}

    parsed_limit, err = parse_positive_int(max_results, "max_results", 100)
    if err:
        return {"success": False, "message": err}

    is_recursive = parse_bool(recursive, True)
    case_insensitive = parse_bool(ignore_case, False)

    resolved, root, err = resolve_repo_target(path, context, allow_empty_as_root=True)
    if err or not resolved or not root:
        return {"success": False, "message": err or f"Invalid path: {path}"}

    flags = re.IGNORECASE if case_insensitive else 0
    try:
        compiled = re.compile(pattern, flags)
    except re.error as exc:
        return {"success": False, "message": f"Invalid regular expression: {exc}"}

    matches: list[str] = []
    files_searched = 0

    def search_file(fpath: str) -> bool:
        nonlocal files_searched
        if not is_path_within(fpath, root):
            return False
        real_file = os.path.realpath(fpath)
        try:
            if not os.path.isfile(real_file) or os.path.getsize(real_file) > _MAX_GREP_FILE_BYTES:
                return False
            if is_binary_file(real_file):
                return False
            text, _ = read_text_with_fallback(real_file)
        except OSError:
            return False

        files_searched += 1
        rel = relative_path(real_file, root)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if compiled.search(line):
                matches.append(f"{rel}:{line_no}: {line.rstrip()[:300]}")
                if len(matches) >= parsed_limit:
                    return True
        return False

    if os.path.isfile(resolved):
        search_file(resolved)
    elif os.path.isdir(resolved):
        if is_recursive:
            visited_dirs: set[str] = set()
            for dirpath, dirnames, filenames in os.walk(resolved, followlinks=False):
                real_dir = os.path.realpath(dirpath)
                if not is_path_within(real_dir, root) or real_dir in visited_dirs:
                    dirnames[:] = []
                    continue
                visited_dirs.add(real_dir)
                dirnames[:] = [
                    d
                    for d in sorted(dirnames)
                    if d not in IGNORE_DIRECTORIES
                    and not d.startswith(".")
                    and is_path_within(os.path.join(dirpath, d), root)
                ]
                for fname in sorted(filenames):
                    if len(matches) >= parsed_limit:
                        break
                    if search_file(os.path.join(dirpath, fname)):
                        break
                if len(matches) >= parsed_limit:
                    break
        else:
            for fname in sorted(os.listdir(resolved)):
                if len(matches) >= parsed_limit:
                    break
                full = os.path.join(resolved, fname)
                if os.path.isfile(full) and search_file(full):
                    break

    truncated = len(matches) >= parsed_limit
    logger.info(
        f'grep "{pattern}" in {relative_path(resolved, root)}: '
        f"{len(matches)} matches across {files_searched} files"
    )
    return {
        "success": True,
        "pattern": pattern,
        "path": relative_path(resolved, root),
        "match_count": len(matches),
        "truncated": truncated,
        "matches": "\n".join(matches),
    }
