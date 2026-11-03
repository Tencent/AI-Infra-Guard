from mcp_scan.utils.parse import (
    clean_content,
    parse_mcp_invocations,
    parse_tool_invocations,
)


def test_parse_standard_finish():
    content = "<function=finish><parameter=content>done</parameter></function>"
    assert parse_tool_invocations(content) == {"toolName": "finish", "args": {"content": "done"}}


def test_parse_short_finish():
    content = "<finish>报告完成。</finish>"
    assert parse_tool_invocations(content) == {
        "toolName": "finish",
        "args": {"content": "报告完成。"},
    }


def test_clean_content_removes_finish_tag():
    assert clean_content("<finish>报告完成。</finish>") == ""


def test_parse_normal_tool():
    content = "<function=read_file><parameter=path>/tmp/a.py</parameter></function>"
    assert parse_tool_invocations(content) == {
        "toolName": "read_file",
        "args": {"path": "/tmp/a.py"},
    }


# --- Regression tests: XML-attribute parameter form (issue #735) ---
# Some OpenAI-compatible models (e.g. DeepSeek) emit <parameter name="x">
# instead of the documented <parameter=x> form. Both must parse.


def test_parse_attribute_form_double_quotes():
    content = '<function=read_file><parameter name="path">/tmp/a.py</parameter></function>'
    assert parse_tool_invocations(content) == {
        "toolName": "read_file",
        "args": {"path": "/tmp/a.py"},
    }


def test_parse_attribute_form_single_quotes():
    content = "<function=read_file><parameter name='path'>/tmp/a.py</parameter></function>"
    assert parse_tool_invocations(content) == {
        "toolName": "read_file",
        "args": {"path": "/tmp/a.py"},
    }


def test_parse_mixed_parameter_forms_in_one_call():
    content = (
        '<function=write_file><parameter name="path">/tmp/b.py</parameter>'
        "<parameter=content>print('hi')</parameter></function>"
    )
    assert parse_tool_invocations(content) == {
        "toolName": "write_file",
        "args": {"path": "/tmp/b.py", "content": "print('hi')"},
    }


def test_parse_attribute_form_multiple_params():
    content = (
        '<function=think><parameter name="thought">step 1</parameter>'
        '<parameter name="content">analysis</parameter></function>'
    )
    assert parse_tool_invocations(content) == {
        "toolName": "think",
        "args": {"thought": "step 1", "content": "analysis"},
    }


def test_parse_unclosed_finish_attribute_form():
    content = '<function=finish><parameter name="content">final report'
    result = parse_tool_invocations(content)
    assert result == {"toolName": "finish", "args": {"content": "final report"}}


def test_parse_mcp_invocations_attribute_form():
    content = (
        '<mcp_function=get_user_role><parameter name="username">admin</parameter>'
        "</mcp_function>"
    )
    assert parse_mcp_invocations(content) == [
        {"toolName": "get_user_role", "args": {"username": "admin"}}
    ]


def test_legacy_form_still_parses():
    # The documented <parameter=x> form must keep working unchanged.
    content = "<function=finish><parameter=content>done</parameter></function>"
    assert parse_tool_invocations(content) == {"toolName": "finish", "args": {"content": "done"}}
