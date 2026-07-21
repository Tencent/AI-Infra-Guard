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

"""aig-mcp-scan SARIF 2.1.0 result formatter.

Converts the internal scan result (as produced by ``Agent.scan()`` in
standalone/non-AIG mode) into a SARIF (Static Analysis Results Interchange
Format) 2.1.0 JSON document, so results can be natively consumed by GitHub
Code Scanning, Azure DevOps, GitLab Security Dashboard, VS Code's Problems
panel, and other SARIF-aware tooling.

Reference: https://docs.oasis-open.org/sarif/sarif/v2.1.0/

Adapted from skill-scan's sarif_formatter.py, using MCP01-MCP10
risk classification instead of SkillTrustBench T01-T09.
"""

from __future__ import annotations

import hashlib
from typing import Any

TOOL_NAME = "aig-mcp-scan"
SARIF_VERSION = "2.1.0"
SARIF_SCHEMA_URI = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/Schemata/sarif-schema-2.1.0.json"
)
INFORMATION_URI = "https://github.com/Tencent/AI-Infra-Guard"

# MCP01-MCP10 + supplementary risk classifications, mirrored from
# the vuln_review.md prompt's risk table. Declared statically so
# downstream SARIF consumers always have full rule metadata.
_RULE_DEFINITIONS: dict[str, dict[str, dict[str, str]]] = {
    "zh": {
        "MCP01": {"name": "令牌管理与密钥暴露", "desc": "凭据窃取与密钥泄露，如硬编码密钥、环境变量泄露、mcp.json 敏感凭据窃取"},
        "MCP02": {"name": "权限提升与范围蔓延", "desc": "工具权限定义过宽，导致代理获得非必要的系统控制权或数据访问权"},
        "MCP03": {"name": "工具投毒攻击", "desc": "合法 MCP 工具被篡改或注入恶意逻辑，返回虚假/偏见结果以操纵模型"},
        "MCP04": {"name": "软件供应链攻击", "desc": "依赖库篡改、恶意第三方 MCP 服务器或构建脚本中的后门"},
        "MCP05": {"name": "命令注入与执行", "desc": "代理根据不可信输入构造并执行系统命令、Shell 脚本或 API 调用"},
        "MCP06": {"name": "提示注入攻击", "desc": "通过上下文（如 OCR、网页内容）注入恶意指令，劫持模型控制流"},
        "MCP07": {"name": "认证与授权不足", "desc": "MCP 服务器或工具未能有效校验身份，导致跨代理/跨用户的越权操作"},
        "MCP08": {"name": "审计与遥测缺失", "desc": "缺乏对工具调用和上下文更改的不可篡改日志，阻碍安全溯源"},
        "MCP09": {"name": "影子 MCP 服务器", "desc": "未经授权部署的 MCP 实例，常存在默认配置风险或缺乏安全合规监管"},
        "MCP10": {"name": "上下文注入与过度分享", "desc": "敏感上下文在不同会话或代理间共享，导致信息泄露或逻辑干扰"},
        "Name Confusion": {"name": "名称混淆攻击", "desc": "恶意工具注册为常用工具的相似名称，诱导代理错误调用"},
        "Rug Pull Attack": {"name": "拉地毯攻击", "desc": "恶意 MCP 服务在获取信任后突然终止或变更行为，造成拒绝服务或数据丢失"},
        "Tool Shadowing Attack": {"name": "工具阴影攻击", "desc": "通过重定义同名工具来覆盖合法工具的行为"},
        "other": {"name": "其他风险", "desc": "未归入 MCP01-MCP10 分类的其他安全问题"},
    },
    "en": {
        "MCP01": {"name": "Token Mismanagement & Secret Exposure", "desc": "Credential theft and secret leakage, e.g. hardcoded keys, env var leaks, mcp.json credential theft"},
        "MCP02": {"name": "Privilege Escalation via Scope Creep", "desc": "Overly broad tool permissions granting agents unnecessary system control or data access"},
        "MCP03": {"name": "Tool Poisoning", "desc": "Legitimate MCP tools tampered or injected with malicious logic, returning false/biased results to manipulate the model"},
        "MCP04": {"name": "Software Supply Chain Attacks", "desc": "Dependency tampering, malicious third-party MCP servers, or backdoors in build scripts"},
        "MCP05": {"name": "Command Injection & Execution", "desc": "Agent constructs and executes system commands, shell scripts, or API calls from untrusted input"},
        "MCP06": {"name": "Prompt Injection via Contextual Payloads", "desc": "Malicious instructions injected via context (OCR, web content) to hijack model control flow"},
        "MCP07": {"name": "Insufficient Auth & Authz", "desc": "MCP server or tools fail to validate identity, enabling cross-agent/cross-user unauthorized operations"},
        "MCP08": {"name": "Lack of Audit and Telemetry", "desc": "No tamper-proof logging of tool calls and context changes, hindering security traceability"},
        "MCP09": {"name": "Shadow MCP Servers", "desc": "Unauthorized MCP instances with default configurations or lacking security compliance"},
        "MCP10": {"name": "Context Injection & Over-Sharing", "desc": "Sensitive context shared across sessions or agents, causing information leakage or logic interference"},
        "Name Confusion": {"name": "Name Confusion Attack", "desc": "Malicious tool registered with a name similar to a common tool, tricking agents into wrong calls"},
        "Rug Pull Attack": {"name": "Rug Pull Attack", "desc": "Malicious MCP service terminates or changes behavior after gaining trust, causing DoS or data loss"},
        "Tool Shadowing Attack": {"name": "Tool Shadowing Attack", "desc": "Overriding legitimate tool behavior by redefining a same-named tool"},
        "other": {"name": "Other Risk", "desc": "Security issues not covered by the MCP01-MCP10 classification"},
    },
}

# Severity level (free text produced by the LLM, ZH/EN) -> SARIF's 3-tier level.
_LEVEL_MAP: dict[str, str] = {
    "critical": "error",
    "严重": "error",
    "high": "error",
    "高危": "error",
    "medium": "warning",
    "中危": "warning",
    "low": "note",
    "低危": "note",
    "info": "note",
    "informational": "note",
}

# Keyword-based fallback mapping: maps free-text risk types (commonly
# produced by the LLM) to MCP01-MCP10 rule IDs. Checked in order;
# first match wins. Keywords are lowercase for case-insensitive matching.
_KEYWORD_MAP: list[tuple[str, str]] = [
    # MCP01 — Token/credential related
    ("credential", "MCP01"),
    ("token", "MCP01"),
    ("secret", "MCP01"),
    ("api key", "MCP01"),
    ("hardcoded", "MCP01"),
    ("password", "MCP01"),
    ("凭据", "MCP01"),
    ("密钥", "MCP01"),
    ("硬编码", "MCP01"),
    ("信息泄露", "MCP01"),
    ("敏感信息", "MCP01"),
    ("数据外传", "MCP01"),
    ("凭据管理", "MCP01"),
    # MCP03 — Tool poisoning / tampering
    ("tool poisoning", "MCP03"),
    ("tool poisoning attack", "MCP03"),
    ("工具投毒", "MCP03"),
    # MCP05 — Command injection / RCE / code execution
    ("rce", "MCP05"),
    ("command injection", "MCP05"),
    ("code execution", "MCP05"),
    ("command execution", "MCP05"),
    ("remote code", "MCP05"),
    ("os.system", "MCP05"),
    ("eval(", "MCP05"),
    ("arbitrary command", "MCP05"),
    ("代码执行", "MCP05"),
    ("命令注入", "MCP05"),
    ("命令执行", "MCP05"),
    ("任意命令", "MCP05"),
    # MCP06 — Prompt injection
    ("prompt injection", "MCP06"),
    ("提示注入", "MCP06"),
    ("逻辑篡改", "MCP06"),
    ("拉地毯", "Rug Pull Attack"),
    ("rug pull", "Rug Pull Attack"),
    # MCP01 — Data exfiltration / info leak (English)
    ("data exfiltration", "MCP01"),
    ("exfiltrat", "MCP01"),
    ("information leak", "MCP01"),
    ("info leak", "MCP01"),
    ("sensitive data", "MCP01"),
    ("/etc/passwd", "MCP01"),
    # Name Confusion
    ("name confusion", "Name Confusion"),
    ("名称混淆", "Name Confusion"),
    ("leetspeak", "Name Confusion"),
    # MCP07 — Auth issues
    ("authentication", "MCP07"),
    ("authorization", "MCP07"),
    ("unauthorized", "MCP07"),
    ("access control", "MCP07"),
    ("认证", "MCP07"),
    ("授权", "MCP07"),
    # MCP10 — Context leakage
    ("context leak", "MCP10"),
    ("context injection", "MCP10"),
    ("上下文注入", "MCP10"),
    # Tool Shadowing
    ("tool shadow", "Tool Shadowing Attack"),
    ("工具阴影", "Tool Shadowing Attack"),
    # MCP04 — Supply chain
    ("supply chain", "MCP04"),
    ("供应链", "MCP04"),
    ("dependency", "MCP04"),
    # MCP02 — Privilege escalation
    ("privilege escalation", "MCP02"),
    ("权限提升", "MCP02"),
    ("scope creep", "MCP02"),
    # MCP08 — Audit gaps
    ("audit", "MCP08"),
    ("审计", "MCP08"),
    ("logging", "MCP08"),
    # MCP09 — Shadow servers
    ("shadow server", "MCP09"),
    ("影子", "MCP09"),
]


def map_level(level: str) -> str:
    """Normalize a free-text severity level into SARIF's error/warning/note scale."""
    return _LEVEL_MAP.get((level or "").strip().lower(), "note")


def parse_risk_type(risk_type: str) -> tuple[str, str]:
    """Split a ``"MCP05: Command Injection"`` style risk_type into (rule_id, rule_name).

    Falls back to ``("other", <original text>)`` when the text doesn't
    follow the "code: name" convention.
    """
    text = (risk_type or "").strip()
    for sep in (":", "："):
        if sep in text:
            code, _, name = text.partition(sep)
            code, name = code.strip(), name.strip()
            if code:
                # Normalize casing, e.g. "mcp05" -> "MCP05"
                code_norm = code.upper() if code[:1].lower() == "m" and code[1:].isdigit() else code
                return code_norm, (name or code_norm)
    # Check if the text itself is a known rule id (without colon)
    text_lower = text.lower()
    for key in _RULE_DEFINITIONS["zh"]:
        if key.lower() == text_lower:
            return key, text
    if not text:
        return "other", "Uncategorized"

    # Keyword-based fallback: map free-text risk types commonly produced by
    # the LLM (e.g. "RCE", "Data Exfiltration", "Prompt Injection") to the
    # appropriate MCP01-MCP10 rule id.
    for keyword, rule_id in _KEYWORD_MAP:
        if keyword in text_lower:
            table = _RULE_DEFINITIONS["zh"]
            return rule_id, table.get(rule_id, {}).get("name", rule_id)
    return "other", text


def _rule_metadata(rule_id: str, rule_name: str, language: str) -> dict[str, str]:
    """Look up static name/description for a rule id, falling back to LLM-provided name."""
    table = _RULE_DEFINITIONS.get(language, _RULE_DEFINITIONS["zh"])
    meta = table.get(rule_id)
    if meta:
        return {"name": meta["name"], "desc": meta["desc"]}
    return {"name": rule_name, "desc": rule_name}


def _fingerprint(rule_id: str, file_path: str, title: str) -> str:
    """Stable hash used for cross-scan de-duplication (SARIF partialFingerprints)."""
    raw = f"{rule_id}:{file_path}:{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _build_location(vuln: dict[str, Any]) -> dict[str, Any]:
    """Build a SARIF physicalLocation from the optional file/line_start/line_end fields."""
    file_path = vuln.get("file") or "."
    region: dict[str, Any] = {}
    line_start = vuln.get("line_start")
    line_end = vuln.get("line_end")
    if isinstance(line_start, int) and line_start > 0:
        region["startLine"] = line_start
        region["endLine"] = line_end if isinstance(line_end, int) and line_end >= line_start else line_start

    physical_location: dict[str, Any] = {"artifactLocation": {"uri": file_path}}
    if region:
        physical_location["region"] = region
    return {"physicalLocation": physical_location}


def to_sarif(result_meta: dict[str, Any], tool_version: str = "0.0.0", language: str = "zh") -> dict[str, Any]:
    """Convert an internal scan result dict into a SARIF 2.1.0 document.

    Args:
        result_meta: The dict returned by ``Agent.scan()`` (single-stage mode),
            containing at least ``results`` (list of vuln dicts), ``score``,
            ``language`` and ``llm``.
        tool_version: aig-mcp-scan package version, embedded as the tool version.
        language: Report language ("zh"/"en"), used to pick the rule name table.

    Returns:
        A JSON-serializable dict following the SARIF 2.1.0 schema.
    """
    lang = language if language in _RULE_DEFINITIONS else "zh"
    vulns: list[dict[str, Any]] = result_meta.get("results") or []

    used_rules: dict[str, dict[str, str]] = {}
    results: list[dict[str, Any]] = []

    for vuln in vulns:
        title = vuln.get("title", "")
        description = vuln.get("description", "")
        suggestion = vuln.get("suggestion", "")
        level_text = vuln.get("level", "")
        risk_type = vuln.get("risk_type", "")

        rule_id, rule_name = parse_risk_type(risk_type)
        used_rules[rule_id] = _rule_metadata(rule_id, rule_name, lang)

        file_path = vuln.get("file") or "."

        result: dict[str, Any] = {
            "ruleId": rule_id,
            "level": map_level(level_text),
            "message": {"text": title or rule_name},
            "locations": [_build_location(vuln)],
            "partialFingerprints": {
                "primaryLocationLineHash": _fingerprint(rule_id, file_path, title),
            },
            "properties": {
                "description": description,
                "severity": level_text,
            },
        }
        if suggestion:
            result["fixes"] = [{"description": {"text": suggestion}}]
        results.append(result)

    # Ensure the full MCP01-MCP10 + supplementary classification is always declared,
    # even if this scan found no matching vulnerabilities.
    full_table = _RULE_DEFINITIONS[lang]
    rules = [
        {
            "id": rule_id,
            "name": meta["name"],
            "shortDescription": {"text": meta["desc"]},
        }
        for rule_id, meta in full_table.items()
    ]
    # Include any dynamically-encountered rule id not present in the static table
    for rule_id, meta in used_rules.items():
        if rule_id not in full_table:
            rules.append({"id": rule_id, "name": meta["name"], "shortDescription": {"text": meta["desc"]}})

    sarif_doc: dict[str, Any] = {
        "version": SARIF_VERSION,
        "$schema": SARIF_SCHEMA_URI,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": TOOL_NAME,
                        "version": tool_version,
                        "informationUri": INFORMATION_URI,
                        "rules": rules,
                    }
                },
                "results": results,
                "properties": {
                    "securityScore": result_meta.get("score"),
                    "primaryLanguage": result_meta.get("language"),
                    "llm": result_meta.get("llm"),
                    "startTime": result_meta.get("start_time"),
                    "endTime": result_meta.get("end_time"),
                },
            }
        ],
    }
    return sarif_doc
