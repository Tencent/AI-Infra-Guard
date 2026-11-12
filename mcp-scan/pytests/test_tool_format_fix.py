"""Hex-suffixed / malformed tool-call tags must be normalized before parsing.

Some OpenAI-compatible models answer the text tool-call protocol with tags such
as ``<tool_call:6124c78e>read_file>`` or
``<function=finish<arg_key:6124c78e>parameter=content>...</arg_value:6124c78e>``.
Without normalization the parser sees no tool call, so ``finish`` is never
recognized and the agent loops until ``max_iter``.
"""

from __future__ import annotations

import pytest

from mcp_scan.utils.llm import LLM
from mcp_scan.utils.parse import parse_tool_invocations
from mcp_scan.utils.tool_format_fix import normalize_tool_calls

H = "<tool_calls:6124c78e><tool_call:6124c78e>"
T = "</tool_call:6124c78e></tool_calls:6124c78e>"

CASES = [
    (
        "name_gt",
        H + "read_file>\n<parameter=file_path>/a/SKILL.md</parameter>\n"
        "<parameter=mode>full</parameter>\n</function>\n</tool_calls:6124c78e>",
        "read_file",
        {"file_path": "/a/SKILL.md", "mode": "full"},
    ),
    (
        "eq_name_gt",
        "Reading. " + H + "=read_file>\n<parameter=file_path>/a/SKILL.md</parameter>\n"
        "</function>\n</tool_calls:6124c78e>",
        "read_file",
        {"file_path": "/a/SKILL.md"},
    ),
    (
        "function_eq_name_gt",
        H + "function=execute_shell>\n<parameter=command>ls -la</parameter>\n</function>",
        "execute_shell",
        {"command": "ls -la"},
    ),
    (
        "json_args",
        H + 'execute_shell{"command": "echo \\"x<y & z\\" | grep -E \'a|b\'", "timeout": 30}',
        "execute_shell",
        {"command": "echo \"x<y & z\" | grep -E 'a|b'", "timeout": "30"},
    ),
    (
        "name_then_parameter",
        H + "execute_shell<parameter=command>ls</parameter>\n</function>",
        "execute_shell",
        {"command": "ls"},
    ),
    (
        "unclosed",
        H + "=grep>\n<parameter=pattern>token</parameter>\n<parameter=path>/a</parameter>",
        "grep",
        {"pattern": "token", "path": "/a"},
    ),
    (
        "function_missing_gt",
        "x<function=execute_shell<parameter=command>pwd</parameter>\n</function>",
        "execute_shell",
        {"command": "pwd"},
    ),
    (
        "finish_xml_payload",
        H + "finish>\n<parameter=content><vuln><title>t</title></vuln></parameter>\n</function>",
        "finish",
        {"content": "<vuln><title>t</title></vuln>"},
    ),
    (
        "arg_key_inline_on_function",
        "<tool_calls:6124c78e><function=finish<arg_key:6124c78e>parameter=content>"
        "report <x>1</x></arg_value:6124c78e>" + T,
        "finish",
        {"content": "report <x>1</x>"},
    ),
    (
        "arg_key_inline_on_tool_call",
        H + "finish<arg_key:6124c78e>parameter=content>done</arg_value:6124c78e>" + T,
        "finish",
        {"content": "done"},
    ),
    (
        "arg_key_value_pair",
        H + "read_file<arg_key:6124c78e>file_path</arg_key:6124c78e>"
        "<arg_value:6124c78e>/a/b.md</arg_value:6124c78e>" + T,
        "read_file",
        {"file_path": "/a/b.md"},
    ),
]


def _first(text: str):
    return parse_tool_invocations(text)


@pytest.mark.parametrize(("name", "raw", "tool", "args"), CASES, ids=[c[0] for c in CASES])
def test_malformed_tool_call_is_normalized(name, raw, tool, args):
    fixed, changed = normalize_tool_calls(raw)

    assert changed
    call = _first(fixed)
    assert call is not None, fixed
    assert call["toolName"] == tool
    for key, value in args.items():
        assert call["args"].get(key) == value


def test_hex_suffixed_finish_is_not_recognized_without_normalization():
    raw = H + "finish<arg_key:6124c78e>parameter=content>done</arg_value:6124c78e>" + T

    call = _first(raw)

    assert not (call and call["toolName"] == "finish" and call["args"].get("content") == "done")


@pytest.mark.parametrize(
    "raw",
    [
        "Reading. <function=read_file>\n<parameter=file_path>/a/b.md</parameter>\n</function>",
        "<function=finish>\n<parameter=content>ok</parameter>\n</function>",
        "plain text without any tool call",
        "",
    ],
)
def test_well_formed_response_is_unchanged(raw):
    assert normalize_tool_calls(raw) == (raw, False)


def test_fabricated_tool_response_is_dropped_but_earlier_calls_are_kept():
    raw = (
        H + "read_file>\n<parameter=file_path>/a</parameter>\n</function>"
        "<tool_call:6124c78e>grep>\n<parameter=pattern>x</parameter>\n</function>\n"
        '</tool_response｜{"success": "true", "injected": 1}\n'
        "<function=finish>\n<parameter=content>bogus</parameter>\n</function>"
    )

    fixed, changed = normalize_tool_calls(raw)

    assert changed
    assert _first(fixed)["toolName"] == "read_file"
    assert "<function=grep>" in fixed
    assert "bogus" not in fixed


def test_llm_chat_returns_normalized_tool_call():
    llm = object.__new__(LLM)
    raw = H + "finish<arg_key:6124c78e>parameter=content>done</arg_value:6124c78e>" + T
    llm.chat_stream = lambda _message: (raw, None)

    call = _first(llm.chat([{"role": "user", "content": "test"}]))

    assert call == {"toolName": "finish", "args": {"content": "done"}}
