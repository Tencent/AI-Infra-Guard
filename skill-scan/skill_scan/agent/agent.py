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

import os
import re
import time
from typing import Any

from skill_scan.agent.base_agent import BaseAgent
from skill_scan.agent.semantic_auditor import (
    SemanticAuditReport,
    audit_semantic_files,
    is_semantic_slicing_enabled,
)
from skill_scan.tools.dispatcher import ToolDispatcher
from skill_scan.utils.aig_logger import mcpLogger
from skill_scan.utils.extract_vuln import (
    VulnerabilityExtractor,
    extract_explicit_verdict,
    extract_result,
    extract_verdict,
)
from skill_scan.utils.loging import logger
from skill_scan.utils.pre_scan import pre_scan
from skill_scan.utils.project_analyzer import analyze_language, calc_skill_score, get_top_language
from skill_scan.utils.prompt_manager import prompt_manager

# Only .git is fully skipped from tree walks (clone noise).
_TREE_SKIP_DIRS = {".git"}
# Dirs kept visible (but flagged with [!]) in the tree instead of being hidden,
# so that malicious code shipped inside them cannot silently escape the audit
# (issue #631).
_TREE_FLAG_DIRS = {
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".nuxt",
}
# Binary bytecode files kept visible (but flagged with [!]) instead of hidden
# (issue #630).
_TREE_FLAG_EXTS = {".pyc", ".pyo", ".pyd"}
_TREE_SKIP_FILES = {"_VERDICT.txt", "_GROUND_TRUTH.txt", "_EVAL.txt"}

_METADATA_FILENAMES = {".DS_Store", "._DS_Store", "Thumbs.db", "desktop.ini", "._.DS_Store"}
_METADATA_PREFIXES = (".__", "._")

# Text / code extensions the auditor can meaningfully inspect. Binary-only
# packages (e.g. a zip holding just a .docx) have nothing to audit; issue #723
# showed that routing them through the LLM pipeline makes the outcome depend
# on whether the model happens to call finish, splitting identical inputs
# between status=done/score=100 and status=error. A static gate keeps the
# result deterministic instead.
_AUDITABLE_EXTS = {
    ".py", ".pyw", ".pyi", ".pyc", ".pyo", ".pyd",  # bytecode stays auditable (#630/#631)
    ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx",
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env",
    ".json", ".jsonc", ".xml", ".html", ".htm", ".css", ".scss",
    ".md", ".markdown", ".rst", ".txt", "",
    ".go", ".rs", ".java", ".kt", ".kts", ".c", ".h", ".cpp", ".hpp", ".cs",
    ".rb", ".php", ".pl", ".lua", ".r", ".swift", ".m", ".mm",
    ".sql", ".graphql", ".proto",
}


def _is_empty_or_metadata_only(repo_dir: str) -> bool:
    """Check whether the directory is empty or contains only OS metadata files.

    Only .git is pruned here (clone noise): files inside dependency/cache/build
    dirs (_TREE_FLAG_DIRS) and bytecode files still count as auditable content
    (issues #630/#631), so a project hiding payloads there is not "empty".
    """
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d != ".git"]
        for fname in files:
            if fname in _TREE_SKIP_FILES:
                continue
            is_meta = (
                fname in _METADATA_FILENAMES
                or any(fname.startswith(p) for p in _METADATA_PREFIXES)
            )
            if not is_meta:
                return False
    return True


def _is_non_skill_package(repo_dir: str) -> bool:
    """Check whether the package holds nothing the auditor can inspect.

    True when there is no SKILL.md (case-insensitive, any depth) and every
    remaining file has a non-auditable extension (binary documents / media /
    archives such as .docx, .pdf, .png, .zip). Extensionless files
    (LICENSE, Makefile, Dockerfile) count as auditable text, and bytecode
    stays auditable per issues #630/#631, so such packages keep going through
    the full pipeline.
    """
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d != ".git"]
        for fname in files:
            if fname in _TREE_SKIP_FILES or fname in _METADATA_FILENAMES:
                continue
            if any(fname.startswith(p) for p in _METADATA_PREFIXES):
                continue
            if fname.lower() == "skill.md":
                return False
            if os.path.splitext(fname)[1].lower() in _AUDITABLE_EXTS:
                return False
    return True


def _build_repo_tree(repo_dir: str, max_files: int = 200) -> str:
    """Generate a repo directory tree string to inject directly into the initial prompt"""
    lines = []
    total = 0
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = sorted(d for d in dirs if d not in _TREE_SKIP_DIRS)
        rel_root = os.path.relpath(root, repo_dir)
        depth = 0 if rel_root == "." else rel_root.count(os.sep) + 1
        indent = "  " * depth
        folder_name = os.path.basename(root) if rel_root != "." else "."
        # Flag (instead of hide) dependency/cache/build dirs so referenced payloads
        # inside them remain auditable; only .git stays fully skipped (noise).
        dir_flag = " [!]" if rel_root != "." and folder_name in _TREE_FLAG_DIRS else ""
        lines.append(f"{indent}{folder_name}/{dir_flag}")
        for fname in sorted(files):
            ext = os.path.splitext(fname)[1]
            file_flag = (
                " [!]" if ext in _TREE_FLAG_EXTS else ""
            )
            if fname in _TREE_SKIP_FILES:
                continue
            if total >= max_files:
                lines.append(f"{indent}  ... (超过 {max_files} 个文件，已截断)")
                return "\n".join(lines)
            lines.append(f"{indent}  {fname}{file_flag}")
            total += 1
    return "\n".join(lines)


# SkillTrustBench T01-T09 vulnerability classification table -- aig-skill-scan's dedicated audit core
_OUTPUT_FORMAT = """## AI Agent Skill 风险分类

在审计过程中，若发现问题，需从以下分类中选取**最匹配的一个**标签标注到对应文件：

| 编号 | 名称 | 攻击类别 | 依赖目标 | 核心攻击方法 |
|-----|------|---------|---------|------------|
| T01 | 技能指令劫持 | Instructions / Skill text | 当 skill 加载时篡改 agent 当前会话目标或安全约束 |
| T02 | Agent 记忆投毒 | Long-term memory / state storage | 将攻击者控制的规则写入持久记忆，使其持续影响后续会话 |
| T03 | 远程载荷获取与执行 | Code execution channel | 从外部 URL 获取代码，使有效载荷在 skill 审查后仍可变化 |
| T04 | 嵌入恶意代码 | Skill scripts/ 目录 | 在 skill 包内携带恶意脚本，调用时本地执行 |
| T05 | 未授权访问与权限提升 | System permissions / access control | 突破最小权限边界，获取超出任务合法所需的权限 |
| T06 | 系统持久化 | Startup services / scheduled tasks | 安装跨会话后门、钩子、服务或定时任务，在 skill 运行后仍存活 |
| T07 | 工具劫持与欺骗 | Local tools / APIs | 修改、包装、伪造或替换工具，使看似合法的调用执行攻击者逻辑 |
| T08 | 不安全依赖 | Third-party dependencies / supply chain | 通过依赖混淆、拼写劫持或不安全来源引入恶意包或组件 |
| T09 | 不安全 Skill 编码实践 | Skill code / configuration | 暴露可利用缺陷，如硬编码密钥、命令注入、明文敏感数据、不安全临时文件 |

使用"编号: 名称"格式填写最匹配的分类（如 `T01: 技能指令劫持`）；不在上述分类中的问题填 `other:事件类型`；无问题的文件 `category` 留空,多个分类用,(逗号)分隔。

## 返回期望
以 Markdown 格式返回审计报告。对于每个确认的漏洞，必须提供：
- 具体位置：文件路径和行号范围
- 完整代码片段：显示漏洞的代码段
- 技术分析：漏洞原理和利用方法
- 影响评估：可获得的权限和影响范围
- 修复建议：详细的安全加固方案
- 攻击路径：具体的利用步骤（如适用）
严格标准：必须提供完整的漏洞利用路径和影响分析。
若未发现漏洞，输出"未发现安全漏洞"并简要说明审计覆盖范围。"""


_OUTPUT_FORMAT_EN = """## AI Agent Skill Risk Classification

During the audit, if issues are found, select the **best matching** label from the following classification:

| ID | Name | Attack Category | Target | Core Attack Method |
|-----|------|---------|---------|------------|
| T01 | Skill Instruction Hijacking | Instructions / Skill text | Alters the agent's current session goals or safety constraints when the skill is loaded |
| T02 | Agent Memory Poisoning | Long-term memory / state storage | Writes attacker-controlled rules into persistent memory so they continue to affect future sessions |
| T03 | Remote Payload Retrieval and Execution | Code execution channel | Fetches code from an external URL, allowing the effective payload to change after skill review |
| T04 | Embedded Malicious Code | Skill scripts/ directory | Ships malicious scripts inside the skill package and executes them locally when invoked |
| T05 | Unauthorized Access and Privilege Escalation | System permissions / access control | Breaks least-privilege boundaries by obtaining permissions beyond the task's legitimate needs |
| T06 | System Persistence | Startup services / scheduled tasks | Installs cross-session backdoors, hooks, services, or scheduled tasks that survive the skill run |
| T07 | Tool Hijacking and Spoofing | Local tools / APIs | Modifies, wraps, spoofs, or replaces tools so legitimate-looking calls execute attacker logic |
| T08 | Insecure Dependencies | Third-party dependencies / supply chain | Introduces malicious packages or components through dependency confusion, typosquatting, or unsafe sources |
| T09 | Insecure Skill Coding Practices | Skill code / configuration | Exposes exploitable flaws such as hardcoded secrets, command injection, plaintext sensitive data, or unsafe temp files |

Use the "ID: Name" format to fill in the best matching classification (e.g., `T01: Skill Instruction Hijacking`). For issues not in the above classification, fill `other: <event type>`. Leave `category` empty for files with no issues. Multiple classifications are separated by commas.

## Return Expectations
Return the audit report in Markdown format. For each confirmed vulnerability, you must provide:
- Specific location: file path and line number range
- Complete code snippet: the code segment showing the vulnerability
- Technical analysis: vulnerability principles and exploitation methods
- Impact assessment: privileges and scope that can be obtained
- Remediation suggestions: detailed security hardening plan
- Attack path: specific exploitation steps (if applicable)
Strict criteria: must provide complete vulnerability exploitation paths and impact analysis.
If no vulnerabilities are found, output "No security vulnerabilities found" and briefly describe the audit coverage scope."""


_INTERNAL_VERDICT_FORMAT_ZH = """
先返回且只返回一个项目级结论：
<verdict>normal|suspicious|malicious</verdict>
结论衡量 Skill 的整体性质，而不是单条漏洞的风险等级：
- normal：没有达到报告门槛的具体安全问题。
- suspicious：存在真实、可达的漏洞或高风险行为，但没有明确恶意意图证据。High/Critical 漏洞也可以是 suspicious。
- malicious：存在明确攻击意图或行为，例如隐蔽外传、凭据窃取、安全约束劫持、恶意持久化、后门或工具劫持。
不得仅因漏洞数量或 level 为 High/Critical 判定 malicious。
该 verdict 仅供扫描器内部判定，最终对外报告会移除此标签。""".strip()


_VULN_XML_FORMAT_ZH = """
必须满足以下xml格式，多个漏洞返回多个vuln标签
<vuln>
  <title>title</title>
  <desc>
  <!-- Markdown格式漏洞描述 -->
  ## 漏洞详情
  **文件位置**: 
  **漏洞类型**: 
  **风险等级**: 

  ### 技术分析

  ### 攻击路径

  ### 影响评估  
  </desc>
  <risk_type>RiskType</risk_type>
  <level>Level</level>
  <!-- 以下三个为可选的结构化定位字段，用于生成 SARIF 报告；若无法精确定位可留空 -->
  <file>相对于项目根目录的文件路径，如 scripts/setup.sh</file>
  <line_start>起始行号，纯数字</line_start>
  <line_end>结束行号，纯数字，若只有单行可与line_start相同</line_end>
  <suggestion>
  ## 修复建议
  </suggestion>
</vuln>
若无漏洞或漏洞为空,返回<empty>
必须使用中文回复。""".strip()


_INTERNAL_VERDICT_FORMAT_EN = """
First return exactly one project-level verdict:
<verdict>normal|suspicious|malicious</verdict>
The verdict describes the overall nature of the Skill, independently of issue severity:
- normal: no concrete security issue reaches the reporting threshold.
- suspicious: a real, reachable vulnerability or high-risk behavior exists, but there is no clear evidence of malicious intent. A High/Critical vulnerability may still be suspicious.
- malicious: clear attack intent or behavior exists, such as covert exfiltration, credential theft, safety-constraint hijacking, malicious persistence, a backdoor, or tool hijacking.
Never infer malicious merely from the number of findings or a High/Critical level.
This verdict is for internal adjudication only and will be removed from the externally returned report.""".strip()


_VULN_XML_FORMAT_EN = """
Must satisfy the following XML format. Return multiple <vuln> tags for multiple vulnerabilities.
<vuln>
  <title>title</title>
  <desc>
  <!-- Markdown format vulnerability description -->
  ## Vulnerability Details
  **File Location**: 
  **Vulnerability Type**: 
  **Risk Level**: 

  ### Technical Analysis

  ### Attack Path

  ### Impact Assessment  
  </desc>
  <risk_type>RiskType</risk_type>
  <level>Level</level>
  <!-- The following three fields are optional structured location fields used to
       generate the SARIF report; leave empty if the location cannot be pinpointed -->
  <file>File path relative to the project root, e.g. scripts/setup.sh</file>
  <line_start>Starting line number, digits only</line_start>
  <line_end>Ending line number, digits only; same as line_start if a single line</line_end>
  <suggestion>
  ## Remediation Suggestions
  </suggestion>
</vuln>
If no vulnerabilities or empty, return <empty>""".strip()


_LANGUAGE_DIRECTIVE_EN = """

## 语言要求 / Language Requirement
You MUST write ALL textual output in English, including all textual fields in the audit report. Do not use Chinese in the final output.

For the risk_type / category field, keep the Txx code but you MUST use the following English category names (do NOT copy the Chinese names from the table above):
- T01: Skill Instruction Hijacking
- T02: Agent Memory Poisoning
- T03: Remote Payload Retrieval and Execution
- T04: Embedded Malicious Code
- T05: Unauthorized Access and Privilege Escalation
- T06: System Persistence
- T07: Tool Hijacking and Spoofing
- T08: Insecure Dependencies
- T09: Insecure Skill Coding Practices
Example: `T04: Embedded Malicious Code`. For non-listed issues use `other: <event type>` in English."""


def is_vuln_review_output(content: str) -> bool:
    """Validate that the project verdict and report findings agree."""
    findings = VulnerabilityExtractor().extract_vulnerabilities(content)
    has_empty = bool(re.search(r"<empty\s*/?>", content, re.IGNORECASE))
    verdict = extract_explicit_verdict(content)
    if verdict == "normal":
        return has_empty and not findings
    if verdict in {"suspicious", "malicious"}:
        return bool(findings)
    return has_empty or bool(findings)


def is_verdict_output(content: str) -> bool:
    """Check for a supported explicit XML or JSON project verdict."""
    return extract_explicit_verdict(content) is not None


def _strip_internal_verdict(content: str) -> str:
    """Remove the private verdict marker before returning the legacy report."""
    return re.sub(
        r"<verdict>\s*(?:normal|suspicious|malicious)\s*</verdict>\s*",
        "",
        content,
        flags=re.IGNORECASE,
    ).strip()


def _collect_llm_instances(llm: Any, specialized_llms: dict | None) -> list[Any]:
    """Return unique LLM instances that expose ``get_usage_stats``."""
    instances: list[Any] = []
    seen_ids: set[int] = set()
    for obj in [llm, *(specialized_llms.values() if isinstance(specialized_llms, dict) else ())]:
        if obj is None or id(obj) in seen_ids:
            continue
        if callable(getattr(obj, "get_usage_stats", None)):
            seen_ids.add(id(obj))
            instances.append(obj)
    return instances


def _snapshot_llm_usage(llm: Any, specialized_llms: dict | None) -> dict[str, int]:
    """Sum cumulative token counters across main and specialized LLM clients."""
    totals = {
        "calls": 0,
        "prompt_tokens": 0,
        "cached_tokens": 0,
        "uncached_prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "usage_missing_calls": 0,
    }
    for inst in _collect_llm_instances(llm, specialized_llms):
        stats = inst.get_usage_stats()
        if isinstance(stats, dict):
            for key in totals:
                totals[key] += int(stats.get(key) or 0)
    return totals


def _build_scan_token_usage(
    before: dict[str, int],
    after: dict[str, int],
    semantic_usage: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build per-scan token usage summary with semantic-slice breakdown."""
    usage_keys = (
        "calls",
        "prompt_tokens",
        "cached_tokens",
        "uncached_prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "usage_missing_calls",
    )
    usage: dict[str, Any] = {
        key: max(0, after.get(key, 0) - before.get(key, 0))
        for key in usage_keys
    }
    sem = (
        dict(semantic_usage)
        if isinstance(semantic_usage, dict)
        else {key: 0 for key in usage_keys}
    )
    usage["semantic_slice"] = sem
    usage["main_pipeline"] = {
        key: max(0, usage[key] - int(sem.get(key) or 0))
        for key in usage_keys
    }
    return usage


class ScanStage:
    """Defines a single scan stage"""

    def __init__(
        self,
        stage_id: str,
        name: str,
        template: str,
        output_format: str = None,
        output_check_fn=None,
        language: str = "zh",
    ):
        self.stage_id = stage_id
        self.name = name
        self.template = template
        self.output_format = output_format
        self.output_check_fn = output_check_fn
        self.language = language


class ScanPipeline:
    """Standard scan pipeline logic"""

    def __init__(self, agent_wrapper: "Agent"):
        self.agent_wrapper = agent_wrapper
        self.results: dict[str, str] = {}

    async def execute_stage(
        self,
        stage: ScanStage,
        repo_dir: str,
        prompt: str,
        context_data: dict[str, Any] = None,
        inject_repo_tree: bool = False,
        inject_pre_scan: bool = False,
    ) -> str:
        """Execute a single scan stage.

        Args:
            stage: The stage definition
            repo_dir: The project directory
            prompt: User-supplied custom prompt
            context_data: Background info from upstream stages
            inject_repo_tree: Whether to inject the directory tree (needed by Stage 2)
            inject_pre_scan: Whether to inject the static pre-scan results (needed by Stage 2)
        """
        logger.info(f"=== Stage {stage.stage_id}: {stage.name} ===")
        mcpLogger.new_plan_step(stepId=stage.stage_id, stepName=stage.name)

        # Load the prompt template
        instruction = prompt_manager.load_template(stage.template)
        if stage.template in {
            "agents/code_audit",
            "agents/vuln_review",
            "agents/verdict_review",
        }:
            instruction += "\n\n" + prompt_manager.load_template("agents/audit_policy")

        # Append the English directive
        if stage.language == "en":
            instruction = instruction + _LANGUAGE_DIRECTIVE_EN

        # Initialize the stage Agent
        agent = BaseAgent(
            name=f"{stage.name} Agent",
            instruction=instruction,
            llm=self.agent_wrapper.llm,
            dispatcher=self.agent_wrapper.dispatcher,
            specialized_llms=self.agent_wrapper.specialized_llms,
            log_step_id=stage.stage_id,
            debug=self.agent_wrapper.debug,
            output_format=stage.output_format,
            output_check_fn=stage.output_check_fn,
            language=stage.language,
        )
        agent.set_repo_dir(repo_dir)
        await agent.initialize()

        # Build the user message (choose the ZH/EN prompt wording based on language)
        if stage.language == "en":
            user_msg = f"Please perform {stage.name}, the project folder is at {repo_dir}\n{prompt}"
        else:
            user_msg = f"请进行{stage.name}，项目文件夹在 {repo_dir}\n{prompt}"

        if inject_repo_tree:
            repo_tree = _build_repo_tree(repo_dir)
            if stage.language == "en":
                user_msg += (
                    f"\n\nThe following is the complete directory structure of the project for your reference"
                    f" (entries marked with [!] are bytecode files or files inside dependency/cache/build"
                    f" directories — pay special attention to them, as they can hide malicious payloads):\n```\n{repo_tree}\n```"
                )
            else:
                user_msg += (
                    f"\n\n以下是该项目的完整目录结构，供你参考（标注 [!] 的是字节码文件或位于依赖/缓存/构建目录"
                    f"内的文件，请重点审计这些位置，它们可能隐藏恶意载荷）：\n```\n{repo_tree}\n```"
                )

        if inject_pre_scan:
            pre_scan_hints = pre_scan(repo_dir)
            if pre_scan_hints:
                user_msg += f"\n\n{pre_scan_hints}"

        if context_data:
            if stage.language == "en":
                user_msg += "\n\nThe following background information is provided:\n"
            else:
                user_msg += "\n\n有以下背景信息：\n"
            for key, value in context_data.items():
                user_msg += f"{key}:{value}\n\n"

        if stage.language == "en":
            user_msg += "\n\nLanguage: You MUST write the entire final audit report (all reason/category text fields) in English."

        agent.add_user_message(user_msg)

        result = await agent.run()
        self.results[stage.name] = result
        return result


class Agent:
    """aig-skill-scan's main Agent, entry point for the scan pipeline.

    In standalone (non-AIG) mode: single-stage Code Audit that directly
    outputs <vuln> XML — fast, ~3x quicker than the full pipeline.
    In AIG mode: three-stage pipeline (Info Collection → Code Audit →
    Vulnerability Review) for rich frontend step display.
    """

    def __init__(
        self,
        llm,
        specialized_llms: dict = None,
        debug: bool = False,
        language: str = "zh",
        aig_mode: bool = False,
        enable_semantic_slicing: bool | None = None,
    ):
        self.llm = llm
        self.specialized_llms = specialized_llms or {}
        self.debug = debug
        self.language = language
        self.aig_mode = aig_mode
        self.enable_semantic_slicing = (
            is_semantic_slicing_enabled()
            if enable_semantic_slicing is None
            else enable_semantic_slicing
        )
        self.last_verdict: str | None = None
        self.dispatcher = ToolDispatcher()
        self.pipeline = ScanPipeline(self)

    async def _run_semantic_slice_audit(
        self, repo_dir: str, language: str
    ) -> SemanticAuditReport:
        """Audit pure semantic files as isolated slices to resist framing."""
        if not self.enable_semantic_slicing:
            return SemanticAuditReport()
        return await audit_semantic_files(self.llm, repo_dir, language=language)

    async def scan(self, repo_dir: str, prompt: str, language: str = "zh") -> dict:
        """Security audit pipeline.

        Non-AIG mode: single-stage Code Audit → <vuln> XML.
        AIG mode: Info Collection → Code Audit → Vulnerability Review.
        """
        self.last_semantic_report = None
        usage_before = _snapshot_llm_usage(self.llm, self.specialized_llms)
        result_meta = {
            "readme": "",
            "score": 0,
            "language": "",
            "start_time": time.time(),
            "end_time": 0,
            "results": [],
            "llm": self.llm.model_name,
            "token_usage": _build_scan_token_usage(usage_before, usage_before),
        }

        # Empty-project detection: return normal immediately to avoid the Agent
        # hallucinating about an empty directory
        if _is_empty_or_metadata_only(repo_dir):
            logger.info("Project is empty or contains only system metadata files, skipping LLM scan and returning normal")
            if language == "en":
                empty_reason = "The project is empty or contains only system metadata files (e.g. .DS_Store); no auditable content"
            else:
                empty_reason = "项目为空或仅包含系统元数据文件（如 .DS_Store），无可审计内容"
            result_meta.update(
                {
                    "readme": empty_reason,
                    "score": 100,
                    "language": "Other",
                    "end_time": time.time(),
                    "results": [],
                }
            )
            self.last_verdict = "normal"
            mcpLogger.result_update(result_meta)
            return result_meta

        # Non-standard skill package gate (issue #723): a package with no
        # SKILL.md and only binary files (e.g. a zip holding a single .docx)
        # has nothing to audit. Returning here keeps the result deterministic
        # instead of depending on whether the model calls finish, which used
        # to split identical inputs between done/score=100 and error.
        if _is_non_skill_package(repo_dir):
            logger.info(
                "Non-standard skill package (no SKILL.md, no auditable files); skipping LLM scan and returning normal"
            )
            if language == "en":
                non_skill_reason = (
                    "This package is not a standard Agent Skill package "
                    "(no SKILL.md and no auditable code/text files, only binary content). "
                    "There is no skill content to audit, so the scan finishes as not-a-skill-package."
                )
            else:
                non_skill_reason = (
                    "该压缩包不是标准的 Agent Skill 项目（未包含 SKILL.md，也不含可审计的代码/文本文件，"
                    "仅含二进制内容）。无 Skill 内容可审计，扫描以非标准 Skill 包结论结束。"
                )
            result_meta.update(
                {
                    "readme": non_skill_reason,
                    "score": 100,
                    "language": "Other",
                    "end_time": time.time(),
                    "results": [],
                }
            )
            self.last_verdict = "normal"
            mcpLogger.result_update(result_meta)
            return result_meta

        if self.aig_mode:
            scan_res = await self._scan_three_stage(repo_dir, prompt, language, result_meta)
        else:
            scan_res = await self._scan_single_stage(repo_dir, prompt, language, result_meta)
        usage_after = _snapshot_llm_usage(self.llm, self.specialized_llms)
        sem_usage = getattr(self.last_semantic_report, "token_usage", None)
        token_usage = _build_scan_token_usage(usage_before, usage_after, sem_usage)
        scan_res["token_usage"] = token_usage
        logger.info(
            f"Token usage: calls={token_usage['calls']} "
            f"prompt={token_usage['prompt_tokens']} "
            f"cached={token_usage['cached_tokens']} "
            f"completion={token_usage['completion_tokens']} "
            f"total={token_usage['total_tokens']} "
            f"(semantic_slice={token_usage['semantic_slice']['total_tokens']}, "
            f"slice_cached={token_usage['semantic_slice'].get('cached_tokens', 0)})"
        )
        mcpLogger.result_update(scan_res)
        return scan_res

    async def _scan_single_stage(
        self, repo_dir: str, prompt: str, language: str, result_meta: dict
    ) -> dict:
        """Single-stage: Code Audit that directly outputs <vuln> XML."""

        if language == "en":
            stage_name = "Code Audit"
            output_format = (
                _OUTPUT_FORMAT_EN
                + "\n\n"
                + _INTERNAL_VERDICT_FORMAT_EN
                + "\n\n"
                + _VULN_XML_FORMAT_EN
                + _LANGUAGE_DIRECTIVE_EN
            )
        else:
            stage_name = "代码审计"
            output_format = (
                _OUTPUT_FORMAT
                + "\n\n"
                + _INTERNAL_VERDICT_FORMAT_ZH
                + "\n\n"
                + _VULN_XML_FORMAT_ZH
            )

        semantic_report = await self._run_semantic_slice_audit(repo_dir, language)
        semantic_hints = semantic_report.to_prompt_hints(language)
        stage1_context = (
            {
                "Isolated Semantic Slice Findings"
                if language == "en"
                else "去语境化语义切片审计线索": semantic_hints
            }
            if semantic_hints
            else None
        )

        audit_result = await self.pipeline.execute_stage(
            ScanStage(
                "1",
                stage_name,
                "agents/code_audit",
                output_format=output_format,
                output_check_fn=is_vuln_review_output,
                language=language,
            ),
            repo_dir,
            prompt,
            stage1_context,
            inject_repo_tree=True,
            inject_pre_scan=True,
        )

        # Extract vuln results from the <vuln> XML output
        extractor = VulnerabilityExtractor()
        vuln_results = extractor.extract_vulnerabilities(audit_result)

        # Fallback: if extraction fails, use extract_result as a fallback
        if not vuln_results:
            parsed = extract_result(audit_result)
            if parsed:
                vuln_results = [parsed]
        verdict = extract_verdict(audit_result, vuln_results) or "suspicious"

        # If continuous-context Code Audit produced no findings (either lulled
        # into normal by narrative framing or degraded without <vuln> blocks),
        # surface the isolated semantic-slice findings to Verdict Review.
        rescued_from_semantic_slices = False
        if not vuln_results and semantic_report.slice_findings:
            slice_xml = semantic_report.to_vuln_xml()
            slice_vulns = extractor.extract_vulnerabilities(slice_xml)
            if slice_vulns:
                audit_result = slice_xml
                vuln_results = slice_vulns
                verdict = semantic_report.highest_verdict
                rescued_from_semantic_slices = True

        # A suspicious first-pass verdict is the ambiguous boundary with the
        # most false positives. Run a focused evidence adjudication only for
        # this class; normal and clearly malicious results keep the fast path.
        if verdict == "suspicious" or rescued_from_semantic_slices:
            draft_for_review = audit_result
            if rescued_from_semantic_slices:
                stripped_draft = _strip_internal_verdict(audit_result)
                if language == "en":
                    draft_for_review = (
                        "[Rescued from Isolated Semantic Slice Audit — continuous Code Audit "
                        "produced no findings; treat these slice <vuln> items strictly as "
                        "unverified draft leads and adjudicate independently against full-file "
                        "context]\n"
                        f"{stripped_draft}"
                    )
                else:
                    draft_for_review = (
                        "[隔离语义切片审计救援草稿——连续代码审计未检出风险；"
                        "请仅将以下切片 <vuln> 条目视为未经全文验证的候选线索，"
                        "对照项目完整上下文独立裁决]\n"
                        f"{stripped_draft}"
                    )
            review_context = {"Draft audit report": draft_for_review}
            if semantic_hints:
                review_context[
                    "Isolated Semantic Slice Findings"
                    if language == "en"
                    else "去语境化语义切片审计线索"
                ] = semantic_hints
            review_result = await self.pipeline.execute_stage(
                ScanStage(
                    "2",
                    "Verdict Review" if language == "en" else "结论复核",
                    "agents/verdict_review",
                    output_format=(
                        "Return exactly one tag and no other text: "
                        "<verdict>normal|suspicious|malicious</verdict>"
                    ),
                    output_check_fn=is_verdict_output,
                    language=language,
                ),
                repo_dir,
                prompt,
                review_context,
                inject_repo_tree=True,
                inject_pre_scan=True,
            )
            verdict = extract_verdict(review_result) or verdict
        if verdict == "normal":
            vuln_results = []
        elif not vuln_results:
            # The legacy response has no project-verdict field. Never expose a
            # risk verdict that external consumers cannot substantiate from
            # the returned findings.
            logger.warning("Risk verdict has no parseable findings; returning normal")
            verdict = "normal"
        self.last_verdict = verdict
        external_audit_result = _strip_internal_verdict(audit_result)
        if verdict == "normal":
            external_audit_result = "<empty>"

        elapsed_time = (time.time() - result_meta["start_time"]) / 60
        logger.info(f"Scan completed, total elapsed time {elapsed_time:.2f} minutes")

        lang_stats = analyze_language(repo_dir)
        top_language = get_top_language(lang_stats)
        safety_score = calc_skill_score(vuln_results)

        result_meta.update(
            {
                "readme": external_audit_result,
                "score": safety_score,
                "language": top_language,
                "end_time": time.time(),
                "results": vuln_results,
            }
        )
        return result_meta

    async def _scan_three_stage(
        self, repo_dir: str, prompt: str, language: str, result_meta: dict
    ) -> dict:
        """Three-stage pipeline: Info Collection → Code Audit → Vulnerability Review."""

        # Stage 1: Info Collection
        if language == "en":
            info_ret_format = (
                "Generate a detailed information collection report in Markdown format, "
                "based on input data. The report should include: project overview, "
                "SKILL.md metadata analysis, tools/scripts inventory, dependencies and resources, "
                "technical analysis (language/framework/entry points), and security assessment "
                "(permission requirements/network exposure). "
                "You MUST write the entire report in English."
            )
            stage1_name = "Info Collection"
            ctx_key1 = "Info Collection Report"
        else:
            info_ret_format = (
                "生成详细的信息收集报告，Markdown格式，基于输入数据如实总结。"
                "报告需包含：项目概述、SKILL.md 元数据分析、工具/脚本清单、依赖与资源、"
                "技术分析（语言/框架/入口）、安全评估（权限需求/网络暴露面）。"
                "必须使用中文回复。"
            )
            stage1_name = "信息收集"
            ctx_key1 = "信息收集报告"
        info_collection = await self.pipeline.execute_stage(
            ScanStage(
                "1",
                stage1_name,
                "agents/project_summary",
                output_format=info_ret_format,
                language=language,
            ),
            repo_dir,
            prompt,
            # Safety net: if dir_tree/ls tool calls fail (issue #629), the
            # discovery stage still has a real file tree to summarize.
            inject_repo_tree=True,
        )

        # Stage 2: Code Audit -- reuses the SkillTrustBench T01-T09 core
        semantic_report = await self._run_semantic_slice_audit(repo_dir, language)
        semantic_hints = semantic_report.to_prompt_hints(language)
        if language == "en":
            audit_ret_format = _OUTPUT_FORMAT_EN + _LANGUAGE_DIRECTIVE_EN
            stage2_name = "Code Audit"
            semantic_key = "Isolated Semantic Slice Findings"
        else:
            audit_ret_format = _OUTPUT_FORMAT
            stage2_name = "代码审计"
            semantic_key = "去语境化语义切片审计线索"
        stage2_context = {ctx_key1: info_collection}
        if semantic_hints:
            stage2_context[semantic_key] = semantic_hints
        code_audit = await self.pipeline.execute_stage(
            ScanStage(
                "2",
                stage2_name,
                "agents/code_audit",
                output_format=audit_ret_format,
                language=language,
            ),
            repo_dir,
            prompt,
            stage2_context,
            inject_repo_tree=True,
            inject_pre_scan=True,
        )

        # Stage 3: Vulnerability Review
        if language == "en":
            review_format = _VULN_XML_FORMAT_EN + _LANGUAGE_DIRECTIVE_EN
            stage3_name = "Vulnerability Review"
            ctx_key3 = "Code Audit Report"
        else:
            review_format = _VULN_XML_FORMAT_ZH
            stage3_name = "漏洞整理"
            ctx_key3 = "代码审计报告"
        stage3_context = {ctx_key3: code_audit}
        if semantic_hints:
            stage3_context[semantic_key] = semantic_hints
        vuln_review = await self.pipeline.execute_stage(
            ScanStage(
                "3",
                stage3_name,
                "agents/vuln_review",
                output_format=review_format,
                output_check_fn=is_vuln_review_output,
                language=language,
            ),
            repo_dir,
            prompt,
            stage3_context,
        )

        # Extract results + compute score
        extractor = VulnerabilityExtractor()
        vuln_results = extractor.extract_vulnerabilities(vuln_review)

        # Fallback: if extraction fails, use extract_result as a fallback
        if not vuln_results:
            parsed = extract_result(vuln_review)
            if parsed:
                vuln_results = [parsed]
        verdict = extract_verdict(vuln_review, vuln_results) or "suspicious"
        if verdict == "normal":
            vuln_results = []
        elif not vuln_results:
            logger.warning("Risk verdict has no parseable findings; returning normal")
            verdict = "normal"
        self.last_verdict = verdict

        elapsed_time = (time.time() - result_meta["start_time"]) / 60
        logger.info(f"Scan task completed, total elapsed time {elapsed_time:.2f} minutes")

        lang_stats = analyze_language(repo_dir)
        top_language = get_top_language(lang_stats)
        safety_score = calc_skill_score(vuln_results)

        result_meta.update(
            {
                "readme": info_collection,
                "score": safety_score,
                "language": top_language,
                "end_time": time.time(),
                "results": vuln_results,
            }
        )
        return result_meta

    async def close(self):
        await self.dispatcher.close()
