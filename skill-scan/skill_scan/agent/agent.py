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
import time
from typing import Any

from skill_scan.agent.base_agent import BaseAgent
from skill_scan.tools.dispatcher import ToolDispatcher
from skill_scan.utils.aig_logger import mcpLogger
from skill_scan.utils.extract_vuln import VulnerabilityExtractor, extract_result
from skill_scan.utils.loging import logger
from skill_scan.utils.pre_scan import pre_scan
from skill_scan.utils.project_analyzer import analyze_language, calc_skill_score, get_top_language
from skill_scan.utils.prompt_manager import prompt_manager

_TREE_SKIP_DIRS = {
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".nuxt",
}
_TREE_SKIP_EXTS = {".pyc", ".pyo", ".pyd"}
_TREE_SKIP_FILES = {"_VERDICT.txt", "_GROUND_TRUTH.txt", "_EVAL.txt"}

_METADATA_FILENAMES = {".DS_Store", "._DS_Store", "Thumbs.db", "desktop.ini", "._.DS_Store"}
_METADATA_PREFIXES = (".__", "._")


def _is_empty_or_metadata_only(repo_dir: str) -> bool:
    """Check whether the directory is empty or contains only OS metadata files"""
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in _TREE_SKIP_DIRS]
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
        lines.append(f"{indent}{folder_name}/")
        for fname in sorted(files):
            if os.path.splitext(fname)[1] in _TREE_SKIP_EXTS:
                continue
            if fname in _TREE_SKIP_FILES:
                continue
            if total >= max_files:
                lines.append(f"{indent}  ... (超过 {max_files} 个文件，已截断)")
                return "\n".join(lines)
            lines.append(f"{indent}  {fname}")
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
    """Check whether the output contains a valid <vuln> XML structure or an <empty> marker"""
    return "<vuln>" in content or "<empty>" in content


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
                user_msg += f"\n\nThe following is the complete directory structure of the project for your reference:\n```\n{repo_tree}\n```"
            else:
                user_msg += f"\n\n以下是该项目的完整目录结构，供你参考：\n```\n{repo_tree}\n```"

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
    """aig-skill-scan's main Agent, the entry point for the three-stage pipeline."""

    def __init__(
        self,
        llm,
        specialized_llms: dict = None,
        debug: bool = False,
        language: str = "zh",
    ):
        self.llm = llm
        self.specialized_llms = specialized_llms or {}
        self.debug = debug
        self.language = language
        self.dispatcher = ToolDispatcher()
        self.pipeline = ScanPipeline(self)

    async def scan(self, repo_dir: str, prompt: str, language: str = "zh") -> dict:
        """Three-stage security audit pipeline.

        Stage 1: Info Collection -- gathers SKILL.md metadata, tool definitions, dependencies, entry scripts
        Stage 2: Code Audit -- code audit powered by the SkillTrustBench T01-T09 core
        Stage 3: Vulnerability Review -- consolidates results (outputs <vuln> XML)
        """
        result_meta = {
            "readme": "",
            "score": 0,
            "language": "",
            "start_time": time.time(),
            "end_time": 0,
            "results": [],
            "llm": self.llm.model_name,
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
            mcpLogger.result_update(result_meta)
            return result_meta

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
        )

        # Stage 2: Code Audit -- reuses the SkillTrustBench T01-T09 core
        if language == "en":
            audit_ret_format = _OUTPUT_FORMAT_EN + _LANGUAGE_DIRECTIVE_EN
            stage2_name = "Code Audit"
            ctx_key2 = "Code Audit Report"
        else:
            audit_ret_format = _OUTPUT_FORMAT
            stage2_name = "代码审计"
            ctx_key2 = "代码审计报告"
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
            {ctx_key1: info_collection},
            inject_repo_tree=True,
            inject_pre_scan=True,
        )

        # Stage 3: Vulnerability Review
        if language == "en":
            review_format = """
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
  <suggestion>
  ## Remediation Suggestions
  </suggestion>
</vuln>
If no vulnerabilities or empty, return <empty>
""".strip()
            review_format += _LANGUAGE_DIRECTIVE_EN
            stage3_name = "Vulnerability Review"
            ctx_key3 = "Code Audit Report"
        else:
            review_format = """
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
  <suggestion>
  ## 修复建议
  </suggestion>
</vuln>
若无漏洞或漏洞为空,返回<empty>
必须使用中文回复。
""".strip()
            stage3_name = "漏洞整理"
            ctx_key3 = "代码审计报告"
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
            {ctx_key3: code_audit},
        )

        # Extract results + compute score
        extractor = VulnerabilityExtractor()
        vuln_results = extractor.extract_vulnerabilities(vuln_review)

        # Fallback: if extraction fails, use extract_result as a fallback
        if not vuln_results:
            parsed = extract_result(vuln_review)
            if parsed:
                vuln_results = [parsed]

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
        mcpLogger.result_update(result_meta)
        return result_meta

    async def close(self):
        await self.dispatcher.close()
