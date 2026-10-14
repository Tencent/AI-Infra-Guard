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

"""Normalize LLM tool calls that miss required args or use legacy names.

Issue #629: qwen/glm-class models often emit think/dir_tree/execute_shell
invocations without the documented parameter tags (or with mcp-scan legacy
names). Passing those empty kwargs into the Python tool raises TypeError
("missing 1 required positional argument: 'thought'/'command'") and the
discovery phase then finishes with an empty report.

This module recovers what it can and otherwise returns a retryable error
that names the missing argument and shows the correct call format.
"""

from __future__ import annotations

import inspect
import re
from typing import Any, Iterable, Optional

from skill_scan.utils.parse import RAW_BODY_ARG

_INJECTED_PARAMS = {"context", "agent_state", "self", "cls"}

# Wrong / legacy names vs the current skill-scan schema (no execute_shell).
_TOOL_ALIASES = {
    "tree": "dir_tree",
    "directory_tree": "dir_tree",
    "list_tree": "dir_tree",
    "list_dir": "ls",
    "list_directory": "ls",
    "listdir": "ls",
    "list_files": "ls",
    "read": "read_file",
    "cat": "read_file",
    "open_file": "read_file",
}

_LEGACY_SHELL_TOOLS = {
    "execute_shell",
    "execute_shell_background",
    "shell",
    "bash",
    "run_command",
    "run_shell",
    "run",
}

_ARG_ALIASES = {
    "thought": ("thinking", "think", "content", "text", "message", "reasoning", "analysis"),
    "path": ("dir", "directory", "folder", "dir_path", "target", "root", "cwd"),
    "file_path": ("path", "file", "filename", "filepath", "target"),
    "pattern": ("regex", "query", "search", "keyword", "text"),
    "command": ("cmd", "shell", "bash", "code", "script"),
    "content": ("text", "message", "result", "report", "output", "summary"),
}

_PATH_TOOLS = {"dir_tree", "ls"}
_LISTING_CMD_RE = re.compile(
    r"^\s*(?:sudo\s+)?(?:ls|dir|tree|find|dir_tree|ll|lsd)\b",
    re.IGNORECASE,
)
_PATH_TOKEN_RE = re.compile(r"^(?:\./|\.\./|/|[A-Za-z]:[\\/])")


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _looks_like_path(value: str) -> bool:
    text = value.strip()
    if not text or "\n" in text or len(text) > 512:
        return False
    if _PATH_TOKEN_RE.match(text):
        return True
    if re.match(r"^[\w.:/\\-]+$", text) and ("/" in text or "\\" in text):
        return True
    return False


def required_params(func) -> list[str]:
    required: list[str] = []
    for name, param in inspect.signature(func).parameters.items():
        if name in _INJECTED_PARAMS:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if param.default is inspect.Parameter.empty:
            required.append(name)
    return required


def allowed_params(func) -> set[str]:
    names: set[str] = set()
    for name, param in inspect.signature(func).parameters.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return set()  # caller may pass anything
        names.add(name)
    return names


def canonicalize_tool_name(tool_name: str, known_names: Iterable[str]) -> str:
    raw = (tool_name or "").strip().strip("\"'")
    if not raw:
        return raw
    known = {name: name for name in known_names}
    known_lower = {name.lower(): name for name in known_names}
    lower = raw.lower()
    if lower in _TOOL_ALIASES:
        return _TOOL_ALIASES[lower]
    if raw in known:
        return known[raw]
    if lower in known_lower:
        return known_lower[lower]
    return raw


def _copy_aliases(args: dict[str, Any], dest: str) -> None:
    if not _is_blank(args.get(dest)):
        return
    for alt in _ARG_ALIASES.get(dest, ()):
        if not _is_blank(args.get(alt)):
            args[dest] = args[alt]
            return


def apply_arg_aliases(tool_name: str, args: dict[str, Any], func) -> dict[str, Any]:
    """Fill documented parameter names from common aliases / leftover body text."""
    normalized = dict(args)
    params = [name for name in inspect.signature(func).parameters if name not in _INJECTED_PARAMS]
    required = required_params(func)

    for dest in params:
        _copy_aliases(normalized, dest)

    raw = normalized.pop(RAW_BODY_ARG, None)
    if isinstance(raw, str) and raw.strip():
        for dest in required:
            if not _is_blank(normalized.get(dest)):
                continue
            if dest in {"path", "file_path"} and not _looks_like_path(raw):
                continue
            normalized[dest] = raw
            break

    return normalized


def default_path_from_context(tool_name: str, args: dict[str, Any], context: Any) -> dict[str, Any]:
    if tool_name not in _PATH_TOOLS:
        return args
    if not _is_blank(args.get("path")):
        return args
    folder = getattr(context, "folder", None) if context is not None else None
    if folder:
        args = dict(args)
        args["path"] = folder
    return args


def _path_from_listing_command(command: str) -> str | None:
    if not command:
        return None
    for tok in command.strip().split()[1:]:
        if tok.startswith("-"):
            continue
        if tok in {"type", "f", "d", "-type", "-name", "-maxdepth"}:
            continue
        return tok
    return None


def remap_legacy_shell(
    tool_name: str,
    args: dict[str, Any],
    context: Any,
) -> tuple[str, dict[str, Any]] | str:
    """Map execute_shell-style listing calls onto dir_tree, or return an error."""
    command = ""
    for key in ("command", "cmd", "shell", RAW_BODY_ARG):
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            command = value.strip()
            break

    folder = getattr(context, "folder", None) if context is not None else None
    listing = (not command) or bool(_LISTING_CMD_RE.match(command))
    if listing:
        path = _path_from_listing_command(command) or folder
        if path:
            return "dir_tree", {"path": path, "_recovered_from": tool_name}
        return missing_arg_error(
            tool_name="dir_tree",
            missing=["path"],
            required=["path"],
            extra=(
                f"Tool '{tool_name}' is not available in skill-scan. "
                "Use dir_tree or ls to list the project directory."
            ),
        )

    return (
        f"Error: Tool '{tool_name}' is not available in skill-scan "
        f"(no shell execution). Use dir_tree/ls to list directories, "
        f"read_file to read files, or grep to search. "
        f"Received command={command!r}."
    )


def missing_arg_error(
    tool_name: str,
    missing: list[str],
    required: list[str],
    extra: str = "",
) -> str:
    example_params = "".join(
        f"<parameter={name}>VALUE</parameter>\n" for name in required
    )
    missing_list = ", ".join(f"'{name}'" for name in missing)
    required_list = ", ".join(required) if required else "(none)"
    hint = extra + "\n" if extra else ""
    return (
        f"Error: Tool '{tool_name}' is missing required argument(s): {missing_list}.\n"
        f"{hint}"
        f"Required arguments: {required_list}.\n"
        "Retry with this exact format (do not omit the parameter tags):\n"
        f"<function={tool_name}>\n"
        f"{example_params}"
        "</function>"
    )


def unknown_tool_error(tool_name: str, available: Iterable[str]) -> str:
    names = ", ".join(available)
    return (
        f"Error: Tool '{tool_name}' not found. "
        f"Available skill-scan tools: {names}. "
        "Do not call execute_shell; use dir_tree or ls to inspect the project."
    )


def filter_allowed_args(func, args: dict[str, Any]) -> dict[str, Any]:
    allowed = allowed_params(func)
    if not allowed:
        return dict(args)
    return {k: v for k, v in args.items() if k in allowed}


def prepare_tool_call(
    tool_name: str,
    args: Optional[dict[str, Any]],
    context: Any,
    *,
    get_tool,
    known_names: Iterable[str],
    available_prompt_tools: Iterable[str],
) -> tuple[str, dict[str, Any], Optional[str]]:
    """Return (canonical_name, kwargs, error). error is set when the call cannot run."""
    incoming = dict(args or {})
    canonical = canonicalize_tool_name(tool_name, known_names)

    if canonical.lower() in _LEGACY_SHELL_TOOLS or tool_name.lower() in _LEGACY_SHELL_TOOLS:
        remapped = remap_legacy_shell(tool_name, incoming, context)
        if isinstance(remapped, str):
            return canonical, incoming, remapped
        canonical, incoming = remapped

    func = get_tool(canonical)
    if func is None:
        return canonical, incoming, unknown_tool_error(tool_name, available_prompt_tools)

    incoming = apply_arg_aliases(canonical, incoming, func)
    incoming = default_path_from_context(canonical, incoming, context)

    missing = [name for name in required_params(func) if _is_blank(incoming.get(name))]
    if missing:
        return (
            canonical,
            incoming,
            missing_arg_error(canonical, missing, required_params(func)),
        )

    incoming.pop("_recovered_from", None)
    incoming = filter_allowed_args(func, incoming)
    return canonical, incoming, None
