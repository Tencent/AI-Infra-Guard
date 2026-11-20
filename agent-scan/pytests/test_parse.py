"""Tool-call parsing tests for agent-scan."""

from agent_scan.utils.parse import clean_content, parse_tool_invocations


def test_parse_equals_form():
    content = "<function=read_file><parameter=path>/tmp/a.py</parameter></function>"
    assert parse_tool_invocations(content) == {
        "toolName": "read_file",
        "args": {"path": "/tmp/a.py"},
    }


def test_parse_function_attribute_form():
    content = (
        '<function name="read_file"><parameter name="path">/tmp/a.py</parameter>'
        "</function>"
    )
    assert parse_tool_invocations(content) == {
        "toolName": "read_file",
        "args": {"path": "/tmp/a.py"},
    }


def test_parse_function_attribute_form_with_other_attributes():
    content = (
        '<function id="1" name="read_file"><parameter=path>/tmp/a.py</parameter>'
        "</function>"
    )
    assert parse_tool_invocations(content) == {
        "toolName": "read_file",
        "args": {"path": "/tmp/a.py"},
    }


def test_clean_content_removes_attribute_form_function():
    content = '<function name="finish"><parameter=content>done</parameter></function>'
    assert clean_content(content) == ""
