from utils.parse import clean_content, parse_tool_invocations


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
