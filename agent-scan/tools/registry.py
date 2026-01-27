import inspect
import os
import re
from collections.abc import Callable
from functools import wraps
from inspect import signature
from pathlib import Path
from typing import Any
from utils.logging import logger

tools: list[dict[str, Any]] = []
_tools_by_name: dict[str, Callable[..., Any]] = {}


def _load_xml_schema(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        content = path.read_text()
        # Simplified parsing using regex
        tools_dict = {}
        tool_pattern = r'<tool name="([^"]+)">.*?</tool>'
        matches = re.finditer(tool_pattern, content, re.DOTALL)
        for match in matches:
            tools_dict[match.group(1)] = match.group(0)
        return tools_dict
    except Exception as e:
        logger.warning(f"Error loading schema file {path}: {e}")
        return {}


def _get_module_name(func: Callable[..., Any]) -> str:
    module = inspect.getmodule(func)
    if not module:
        return "unknown"

    module_name = module.__name__
    if ".tools." in module_name:
        parts = module_name.split(".tools.")[-1].split(".")
        if len(parts) >= 1:
            return parts[0]
    return "unknown"


def register_tool(
        func: Callable[..., Any] | None = None, *, sandbox_execution: bool = True
) -> Callable[..., Any]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        func_dict = {
            "name": f.__name__,
            "function": f,
            "module": _get_module_name(f),
            "sandbox_execution": sandbox_execution,
        }

        try:
            module_path = Path(inspect.getfile(f))
            schema_file_name = f"{module_path.stem}_schema.xml"
            schema_path = module_path.parent / schema_file_name

            xml_tools = _load_xml_schema(schema_path)

            if xml_tools is not None and f.__name__ in xml_tools:
                func_dict["xml_schema"] = xml_tools[f.__name__]
            else:
                func_dict["xml_schema"] = (
                    f'<tool name="{f.__name__}">'
                    "<description>Schema not found for tool.</description>"
                    "</tool>"
                )
        except (TypeError, FileNotFoundError) as e:
            logger.warning(f"Error loading schema for {f.__name__}: {e}")
            func_dict["xml_schema"] = (
                f'<tool name="{f.__name__}">'
                "<description>Error loading schema.</description>"
                "</tool>"
            )

        tools.append(func_dict)
        _tools_by_name[str(func_dict["name"])] = f

        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return f(*args, **kwargs)

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


def get_tool_by_name(name: str) -> Callable[..., Any] | None:
    return _tools_by_name.get(name)


def get_tool_names() -> list[str]:
    return list(_tools_by_name.keys())


def needs_agent_state(tool_name: str) -> bool:
    tool_func = get_tool_by_name(tool_name)
    if not tool_func:
        return False
    sig = signature(tool_func)
    return "agent_state" in sig.parameters


def needs_context(tool_name: str) -> bool:
    """检查工具是否需要上下文（context）参数"""
    tool_func = get_tool_by_name(tool_name)
    if not tool_func:
        return False
    sig = signature(tool_func)
    return "context" in sig.parameters


def should_execute_in_sandbox(tool_name: str) -> bool:
    for tool in tools:
        if tool.get("name") == tool_name:
            return bool(tool.get("sandbox_execution", True))
    return True


def get_tools_prompt(tool_list: list = []) -> str:
    selected_tools = []
    if len(tool_list) != 0:
        for tool in tools:
            name = tool.get('name')
            if name in tool_list:
                selected_tools.append(tool)
    else:
        selected_tools = tools

    tools_by_module: dict[str, list[dict[str, Any]]] = {}

    for tool in selected_tools:
        module = tool.get("module", "unknown")
        if module not in tools_by_module:
            tools_by_module[module] = []
        tools_by_module[module].append(tool)

    xml_sections = []
    for module, module_tools in sorted(tools_by_module.items()):
        tag_name = f"tools"
        section_parts = [f"<{tag_name}>"]
        for tool in module_tools:
            tool_xml = tool.get("xml_schema", "")
            if tool_xml:
                indented_tool = "\n".join(f"  {line}" for line in tool_xml.split("\n"))
                section_parts.append(indented_tool)
        section_parts.append(f"</{tag_name}>")
        xml_sections.append("\n".join(section_parts))

    return "\n\n".join(xml_sections)


def clear_registry() -> None:
    tools.clear()
    _tools_by_name.clear()
