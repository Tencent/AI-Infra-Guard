"""Regression tests for issue #629 — malformed / missing-arg tool calls.

Skill-scan discovery used to crash-empty when models (qwen3 / glm) emitted
think / execute_shell / dir_tree calls without the documented parameter tags.
The parser + dispatcher must now either recover or return a retryable error
so the agent can continue inspecting a real project directory.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

import skill_scan.tools  # noqa: F401  # register local tools
from skill_scan.tools.dispatcher import ToolDispatcher
from skill_scan.utils.parse import RAW_BODY_ARG, parse_tool_invocations


def _context(folder: Path) -> SimpleNamespace:
    return SimpleNamespace(folder=str(folder))


def _dispatch(tool_name: str, args: dict, folder: Path | None = None) -> str:
    dispatcher = ToolDispatcher()
    ctx = _context(folder) if folder is not None else None
    return asyncio.run(dispatcher.call_tool(tool_name, args, ctx))


def _parse_and_dispatch(payload: str, folder: Path | None = None) -> tuple[dict | None, str]:
    parsed = parse_tool_invocations(payload)
    assert parsed is not None, f"parser dropped payload: {payload!r}"
    result = _dispatch(parsed["toolName"], parsed["args"], folder)
    return parsed, result


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "SKILL.md").write_text("# demo skill\nUse this skill to greet.\n", encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "hello.py").write_text("print('hi')\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Parser: issue-shaped payloads must yield a usable tool name + recoverable args
# ---------------------------------------------------------------------------

def test_parse_think_missing_thought_keeps_tool_name() -> None:
    parsed = parse_tool_invocations("<function=think>\n</function>")
    assert parsed == {"toolName": "think", "args": {}}


def test_parse_think_body_text_becomes_raw_body() -> None:
    parsed = parse_tool_invocations(
        "<function=think>\nI need to inspect the project structure first.\n</function>"
    )
    assert parsed is not None
    assert parsed["toolName"] == "think"
    assert parsed["args"][RAW_BODY_ARG] == "I need to inspect the project structure first."


def test_parse_think_json_body() -> None:
    parsed = parse_tool_invocations(
        '<function=think>\n{"thought": "plan discovery"}\n</function>'
    )
    assert parsed == {"toolName": "think", "args": {"thought": "plan discovery"}}


def test_parse_think_inline_attribute() -> None:
    parsed = parse_tool_invocations(
        '<function=think thought="need to list files">\n</function>'
    )
    assert parsed == {"toolName": "think", "args": {"thought": "need to list files"}}


def test_parse_execute_shell_missing_command() -> None:
    parsed = parse_tool_invocations("<function=execute_shell>\n</function>")
    assert parsed == {"toolName": "execute_shell", "args": {}}


def test_parse_execute_shell_legacy_cmd_param() -> None:
    parsed = parse_tool_invocations(
        "<function=execute_shell>\n<parameter=cmd>ls /tmp/proj</parameter>\n</function>"
    )
    assert parsed == {"toolName": "execute_shell", "args": {"cmd": "ls /tmp/proj"}}


def test_parse_dir_tree_missing_path() -> None:
    parsed = parse_tool_invocations("<function=dir_tree>\n</function>")
    assert parsed == {"toolName": "dir_tree", "args": {}}


def test_parse_dir_tree_child_tag_path() -> None:
    parsed = parse_tool_invocations(
        "<function=dir_tree>\n<path>/tmp/proj</path>\n</function>"
    )
    assert parsed == {"toolName": "dir_tree", "args": {"path": "/tmp/proj"}}


def test_parse_dir_tree_inline_path_attribute() -> None:
    parsed = parse_tool_invocations(
        '<function=dir_tree path="/tmp/proj">\n</function>'
    )
    assert parsed == {"toolName": "dir_tree", "args": {"path": "/tmp/proj"}}


def test_parse_qwen_tool_call_json() -> None:
    parsed = parse_tool_invocations(
        '<tool_call>\n{"name": "dir_tree", "arguments": {"path": "/tmp/proj"}}\n</tool_call>'
    )
    assert parsed == {"toolName": "dir_tree", "args": {"path": "/tmp/proj"}}


def test_parse_standard_parameter_tags_still_work() -> None:
    parsed = parse_tool_invocations(
        "<function=dir_tree>\n<parameter=path>/tmp/proj</parameter>\n</function>"
    )
    assert parsed == {"toolName": "dir_tree", "args": {"path": "/tmp/proj"}}


def test_parse_named_parameter_attribute_still_works() -> None:
    parsed = parse_tool_invocations(
        '<function=think>\n<parameter name="thought">review SKILL.md</parameter>\n</function>'
    )
    assert parsed == {"toolName": "think", "args": {"thought": "review SKILL.md"}}


# ---------------------------------------------------------------------------
# Dispatcher: missing args / legacy names must not raise, and discovery continues
# ---------------------------------------------------------------------------

def test_think_missing_thought_returns_retryable_error() -> None:
    result = _dispatch("think", {})
    assert "missing required argument" in result
    assert "'thought'" in result
    assert "<function=think>" in result
    assert "<parameter=thought>" in result
    assert "TypeError" not in result
    assert "missing 1 required positional argument" not in result


def test_think_recovers_thought_from_raw_body() -> None:
    result = _dispatch("think", {RAW_BODY_ARG: "Need to list SKILL.md and scripts/"})
    assert "Need to list SKILL.md and scripts/" in result
    assert "missing required argument" not in result


def test_execute_shell_missing_command_recovers_dir_tree(project: Path) -> None:
    parsed, result = _parse_and_dispatch("<function=execute_shell>\n</function>", project)
    assert parsed["toolName"] == "execute_shell"
    assert parsed["args"] == {}
    assert "SKILL.md" in result
    assert "hello.py" in result
    assert "missing 1 required positional argument" not in result
    assert "TypeError" not in result


def test_execute_shell_ls_command_recovers_dir_tree(project: Path) -> None:
    result = _dispatch("execute_shell", {"cmd": f"ls -la {project}"}, project)
    assert "SKILL.md" in result
    assert "scripts" in result


def test_execute_shell_non_listing_returns_clear_error() -> None:
    result = _dispatch("execute_shell", {"command": "python -c 'print(1)'"})
    assert result.startswith("Error:")
    assert "not available" in result
    assert "dir_tree" in result
    assert "missing 1 required positional argument" not in result


def test_dir_tree_missing_path_defaults_to_project(project: Path) -> None:
    parsed, result = _parse_and_dispatch("<function=dir_tree>\n</function>", project)
    assert parsed["args"] == {}
    assert "SKILL.md" in result
    assert "hello.py" in result
    assert "missing required argument" not in result


def test_dir_tree_child_tag_path_executes(project: Path) -> None:
    payload = f"<function=dir_tree>\n<path>{project}</path>\n</function>"
    parsed, result = _parse_and_dispatch(payload, project)
    assert parsed["args"]["path"] == str(project)
    assert "SKILL.md" in result


def test_dir_tree_tool_call_json_executes(project: Path) -> None:
    payload = (
        "<tool_call>\n"
        f'{{"name": "dir_tree", "arguments": {{"path": "{project}"}}}}\n'
        "</tool_call>"
    )
    _, result = _parse_and_dispatch(payload, project)
    assert "SKILL.md" in result


def test_ls_alias_list_dir_recovers(project: Path) -> None:
    result = _dispatch("list_dir", {}, project)
    assert "SKILL.md" in result


def test_read_file_accepts_path_alias(project: Path) -> None:
    result = _dispatch("read_file", {"path": str(project / "SKILL.md")}, project)
    assert "demo skill" in result


def test_unknown_kwargs_do_not_crash(project: Path) -> None:
    result = _dispatch(
        "dir_tree",
        {"path": str(project), "directory": str(project), "extra": "nope"},
        project,
    )
    assert "SKILL.md" in result
    assert "unexpected keyword" not in result


def test_issue_629_payloads_do_not_empty_discovery(project: Path) -> None:
    """End-to-end: every payload shape from #629 continues discovery safely."""
    payloads = [
        "<function=think>\n</function>",
        "<function=think>\nInspect SKILL.md and scripts before auditing.\n</function>",
        "<function=execute_shell>\n</function>",
        "<function=execute_shell>\n<parameter=cmd>ls -la</parameter>\n</function>",
        "<function=dir_tree>\n</function>",
        f"<function=dir_tree>\n<path>{project}</path>\n</function>",
        '<function=dir_tree path="' + str(project) + '">\n</function>',
        (
            "<tool_call>\n"
            f'{{"name": "dir_tree", "arguments": {{"path": "{project}"}}}}\n'
            "</tool_call>"
        ),
    ]

    saw_tree = False
    for payload in payloads:
        parsed, result = _parse_and_dispatch(payload, project)
        assert parsed is not None
        assert "missing 1 required positional argument" not in result
        assert "TypeError" not in result
        assert result, "tool result must not be empty"
        if "SKILL.md" in result:
            saw_tree = True
        if parsed["toolName"] == "think" and not parsed["args"]:
            assert "missing required argument" in result
            assert "thought" in result

    assert saw_tree, "at least one recovered call must list the real project tree"
