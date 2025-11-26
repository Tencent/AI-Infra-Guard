import html
import re
from typing import Any


def parse_tool_invocations(content: str) -> dict[str, Any] | None:
    tool_invocations: dict[str, Any] = {}

    fn_regex_pattern = r"<function=([^>]+)>\n?(.*?)</function.*?>"
    fn_param_regex_pattern = r"<parameter=([^>]+)>(.*?)</parameter>"

    fn_matches = re.finditer(fn_regex_pattern, content, re.DOTALL)

    for fn_match in fn_matches:
        fn_name = fn_match.group(1)
        fn_body = fn_match.group(2)

        param_matches = re.finditer(fn_param_regex_pattern, fn_body, re.DOTALL)

        args = {}
        for param_match in param_matches:
            param_name = param_match.group(1)
            param_value = param_match.group(2).strip()

            param_value = html.unescape(param_value)
            args[param_name] = param_value

        tool_invocations = {"toolName": fn_name, "args": args}
    return tool_invocations if tool_invocations else None


def clean_content(content: str) -> str:
    if not content:
        return ""
    tool_pattern = r"<function=[^>]+>.*?</function.*?>"
    cleaned = re.sub(tool_pattern, "", content, flags=re.DOTALL)

    hidden_xml_patterns = [
        r"<inter_agent_message>.*?</inter_agent_message>",
        r"<agent_completion_report>.*?</agent_completion_report>",
    ]
    for pattern in hidden_xml_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    cleaned = re.sub(r"\n\s*\n", "\n\n", cleaned)

    return cleaned.strip()
