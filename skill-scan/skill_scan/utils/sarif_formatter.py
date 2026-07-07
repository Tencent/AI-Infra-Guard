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

"""aig-skill-scan SARIF 2.1.0 result formatter.

Converts the internal scan result (as produced by ``Agent.scan()`` in
standalone/non-AIG mode) into a SARIF (Static Analysis Results Interchange
Format) 2.1.0 JSON document, so results can be natively consumed by GitHub
Code Scanning, Azure DevOps, GitLab Security Dashboard, VS Code's Problems
panel, and other SARIF-aware tooling.

Reference: https://docs.oasis-open.org/sarif/sarif/v2.1.0/
"""

from __future__ import annotations

import hashlib
from typing import Any

TOOL_NAME = "aig-skill-scan"
SARIF_VERSION = "2.1.0"
SARIF_SCHEMA_URI = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/Schemata/sarif-schema-2.1.0.json"
)
INFORMATION_URI = "https://github.com/Tencent/AI-Infra-Guard"

# SkillTrustBench T01-T09 risk classification, mirrored from agent.py's
# _OUTPUT_FORMAT / _OUTPUT_FORMAT_EN tables, used to populate SARIF's
# runs[].tool.driver.rules[]. Declared statically (independent of what was
# actually found) so downstream SARIF consumers always have full rule
# metadata available.
_RULE_DEFINITIONS: dict[str, dict[str, dict[str, str]]] = {
    "zh": {
        "T01": {"name": "技能指令劫持", "desc": "当 skill 加载时篡改 agent 当前会话目标或安全约束"},
        "T02": {"name": "Agent 记忆投毒", "desc": "将攻击者控制的规则写入持久记忆，使其持续影响后续会话"},
        "T03": {"name": "远程载荷获取与执行", "desc": "从外部 URL 获取代码，使有效载荷在 skill 审查后仍可变化"},
        "T04": {"name": "嵌入恶意代码", "desc": "在 skill 包内携带恶意脚本，调用时本地执行"},
        "T05": {"name": "未授权访问与权限提升", "desc": "突破最小权限边界，获取超出任务合法所需的权限"},
        "T06": {"name": "系统持久化", "desc": "安装跨会话后门、钩子、服务或定时任务，在 skill 运行后仍存活"},
        "T07": {"name": "工具劫持与欺骗", "desc": "修改、包装、伪造或替换工具，使看似合法的调用执行攻击者逻辑"},
        "T08": {"name": "不安全依赖", "desc": "通过依赖混淆、拼写劫持或不安全来源引入恶意包或组件"},
        "T09": {"name": "不安全 Skill 编码实践", "desc": "暴露可利用缺陷，如硬编码密钥、命令注入、明文敏感数据、不安全临时文件"},
        "other": {"name": "其他风险", "desc": "未归入 T01-T09 分类的其他安全问题"},
    },
    "en": {
        "T01": {"name": "Skill Instruction Hijacking", "desc": "Alters the agent's current session goals or safety constraints when the skill is loaded"},
        "T02": {"name": "Agent Memory Poisoning", "desc": "Writes attacker-controlled rules into persistent memory so they continue to affect future sessions"},
        "T03": {"name": "Remote Payload Retrieval and Execution", "desc": "Fetches code from an external URL, allowing the effective payload to change after skill review"},
        "T04": {"name": "Embedded Malicious Code", "desc": "Ships malicious scripts inside the skill package and executes them locally when invoked"},
        "T05": {"name": "Unauthorized Access and Privilege Escalation", "desc": "Breaks least-privilege boundaries by obtaining permissions beyond the task's legitimate needs"},
        "T06": {"name": "System Persistence", "desc": "Installs cross-session backdoors, hooks, services, or scheduled tasks that survive the skill run"},
        "T07": {"name": "Tool Hijacking and Spoofing", "desc": "Modifies, wraps, spoofs, or replaces tools so legitimate-looking calls execute attacker logic"},
        "T08": {"name": "Insecure Dependencies", "desc": "Introduces malicious packages or components through dependency confusion, typosquatting, or unsafe sources"},
        "T09": {"name": "Insecure Skill Coding Practices", "desc": "Exposes exploitable flaws such as hardcoded secrets, command injection, plaintext sensitive data, or unsafe temp files"},
        "other": {"name": "Other Risk", "desc": "Security issues not covered by the T01-T09 classification"},
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


def map_level(level: str) -> str:
    """Normalize a free-text severity level into SARIF's error/warning/note scale."""
    return _LEVEL_MAP.get((level or "").strip().lower(), "note")


def parse_risk_type(risk_type: str) -> tuple[str, str]:
    """Split a ``"T04: 嵌入恶意代码"`` style risk_type into (rule_id, rule_name).

    Falls back to ``("other", <original text>)`` when the text doesn't
    follow the "code: name" convention.
    """
    text = (risk_type or "").strip()
    for sep in (":", "："):
        if sep in text:
            code, _, name = text.partition(sep)
            code, name = code.strip(), name.strip()
            if code:
                # Normalize casing, e.g. "t04" -> "T04"
                code_norm = code.upper() if code[:1].lower() == "t" and code[1:].isdigit() else code
                return code_norm, (name or code_norm)
    if not text:
        return "other", "Uncategorized"
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
        tool_version: aig-skill-scan package version, embedded as the tool version.
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

    # Ensure the full T01-T09 + other classification is always declared,
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
    # (e.g. a custom "other:xxx" free-text risk_type).
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
