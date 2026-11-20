"""Tool-call parsing tests for skill-scan."""

from skill_scan.utils.parse import parse_tool_invocations


def test_mixed_parameter_forms_keep_both():
    content = (
        '<function=write_file><parameter name="path">/tmp/b.py</parameter>'
        "<parameter=content>print('hi')</parameter></function>"
    )
    assert parse_tool_invocations(content) == {
        "toolName": "write_file",
        "args": {"path": "/tmp/b.py", "content": "print('hi')"},
    }


def test_named_parameter_form_still_parses():
    content = '<function=read_file><parameter name="path">/tmp/a.py</parameter></function>'
    assert parse_tool_invocations(content) == {
        "toolName": "read_file",
        "args": {"path": "/tmp/a.py"},
    }


def test_legacy_parameter_form_still_parses():
    content = "<function=read_file><parameter=path>/tmp/a.py</parameter></function>"
    assert parse_tool_invocations(content) == {
        "toolName": "read_file",
        "args": {"path": "/tmp/a.py"},
    }
