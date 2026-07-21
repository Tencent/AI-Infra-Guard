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

from mcp_scan.agent.base_agent import BaseAgent
from mcp_scan.tools.dispatcher import ToolDispatcher
from mcp_scan.utils.aig_logger import mcpLogger
from mcp_scan.utils.extract_vuln import VulnerabilityExtractor, extract_result
from mcp_scan.utils.loging import logger
from mcp_scan.utils.pre_scan import pre_scan
from mcp_scan.utils.project_analyzer import analyze_language, calc_mcp_score, get_top_language
from mcp_scan.utils.prompt_manager import prompt_manager


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


_LANGUAGE_DIRECTIVE_EN = """

## 语言要求 / Language Requirement
You MUST write ALL textual output in English, including all textual fields in the audit report. Do not use Chinese in the final output."""


# MCP01-MCP10 vuln XML format with structured location fields
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
  <file>相对于项目根目录的文件路径，如 src/index.ts</file>
  <line_start>起始行号，纯数字</line_start>
  <line_end>结束行号，纯数字，若只有单行可与line_start相同</line_end>
  <suggestion>
  ## 修复建议
  </suggestion>
</vuln>
若无漏洞或漏洞为空,返回<empty>
必须使用中文回复。""".strip()


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
  <file>File path relative to the project root, e.g. src/index.ts</file>
  <line_start>Starting line number, digits only</line_start>
  <line_end>Ending line number, digits only; same as line_start if a single line</line_end>
  <suggestion>
  ## Remediation Suggestions
  </suggestion>
</vuln>
If no vulnerabilities or empty, return <empty>""".strip()


def is_vuln_review_output(content: str) -> bool:
    """Check whether the output contains a valid <vuln> XML structure or an <empty> marker"""
    return "<vuln>" in content or "<empty>" in content


class ScanStage:
    """定义扫描的一个阶段"""

    def __init__(
        self,
        stage_id: str,
        name: str,
        template: str,
        output_format: str = None,
        output_check_fn=None,
        language="zh",
    ):
        self.stage_id = stage_id
        self.name = name
        self.template = template
        self.output_format = output_format
        self.output_check_fn = output_check_fn
        self.language = language


class ScanPipeline:
    """标准扫描流水线逻辑"""

    def __init__(self, agent_wrapper: "Agent"):
        self.agent_wrapper = agent_wrapper
        self.results = {}

    async def execute_stage(
        self,
        stage: ScanStage,
        repo_dir: str,
        prompt: str,
        context_data: dict[str, Any] = None,
        inject_repo_tree: bool = False,
        inject_pre_scan: bool = False,
    ) -> str:
        logger.info(f"=== 阶段 {stage.stage_id}: {stage.name} ===")
        mcpLogger.new_plan_step(stepId=stage.stage_id, stepName=stage.name)

        # 加载提示词模板
        instruction = prompt_manager.load_template(stage.template)

        # 追加英文语言指令
        if stage.language == "en":
            instruction = instruction + _LANGUAGE_DIRECTIVE_EN

        # 初始化阶段 Agent
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

        # 构造用户消息（根据 language 选择中/英文引导语）
        if stage.language == "en":
            user_msg = f"Please perform {stage.name}, the folder is at {repo_dir}\n{prompt}"
        else:
            user_msg = f"请进行{stage.name}，文件夹在 {repo_dir}\n{prompt}"

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

        # 运行并返回结果
        result = await agent.run()
        self.results[stage.name] = result
        return result

    async def execute_stage_dynamic(
        self, stage: ScanStage, prompt: str, context_data: dict[str, Any] = None
    ) -> str:
        logger.info(f"=== 阶段 {stage.stage_id}: {stage.name} ===")
        mcpLogger.new_plan_step(stepId=stage.stage_id, stepName=stage.name)

        # 加载提示词模板
        instruction = prompt_manager.load_template(stage.template)

        # 初始化阶段 Agent
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
        )
        await agent.initialize()

        # 构造用户消息（根据 language 选择中/英文引导语）
        if stage.language == "en":
            user_msg = f"Please perform {stage.name}, conducting MCP dynamic scanning\n{prompt}"
        else:
            user_msg = f"请进行{stage.name}，进行MCP动态扫描\n{prompt}"
        if context_data:
            if stage.language == "en":
                user_msg += "\n\nThe following background information is provided:\n"
            else:
                user_msg += "\n\n有以下背景信息：\n"
            for key, value in context_data.items():
                user_msg += f"{key}:{value}\n\n"

        agent.add_user_message(user_msg)

        # 运行并返回结果
        result = await agent.run()
        self.results[stage.name] = result
        return result


class Agent:
    """aig-mcp-scan's main Agent, entry point for the scan pipeline.

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
        server_url: str = None,
        language="zh",
        headers=None,
        aig_mode: bool = False,
    ):
        self.llm = llm
        self.specialized_llms = specialized_llms or {}
        self.debug = debug
        self.aig_mode = aig_mode
        self.dispatcher = ToolDispatcher(mcp_server_url=server_url, mcp_headers=headers)
        self.pipeline = ScanPipeline(self)
        self.language = language

    async def scan(self, repo_dir: str, prompt: str, language: str = "zh") -> dict:
        """Security audit pipeline.

        Non-AIG mode: single-stage Code Audit → <vuln> XML.
        AIG mode: Info Collection → Code Audit → Vulnerability Review.
        """
        result_meta = {
            "readme": "",
            "score": 0,
            "language": "",
            "start_time": time.time(),
            "end_time": 0,
            "results": [],
            "llm": self.llm.model,
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

        if self.aig_mode:
            return await self._scan_three_stage(repo_dir, prompt, language, result_meta)
        else:
            return await self._scan_single_stage(repo_dir, prompt, language, result_meta)

    async def _scan_single_stage(
        self, repo_dir: str, prompt: str, language: str, result_meta: dict
    ) -> dict:
        """Single-stage: Code Audit that directly outputs <vuln> XML."""

        if language == "en":
            stage_name = "Code Audit"
            audit_ret_format = """
Return in Markdown format.
For each confirmed vulnerability, you must provide:
- Specific location: file path and line number range
- Complete code snippet: the code segment showing the vulnerability
- Technical analysis: vulnerability principles and exploitation methods
- Impact assessment: privileges and scope that can be obtained
- Remediation suggestions: detailed security hardening plan
- Attack path: specific exploitation steps (if applicable)
Strict criteria: must provide complete vulnerability exploitation paths and impact analysis.
You MUST write the entire report in English.
            """
            output_format = audit_ret_format + "\n\n" + _VULN_XML_FORMAT_EN + _LANGUAGE_DIRECTIVE_EN
        else:
            stage_name = "代码审计"
            audit_ret_format = """
markdown格式返回
对于每个确认的漏洞，必须提供：
- 具体位置：文件路径和行号范围
- 完整代码片段：显示漏洞的代码段
- 技术分析：漏洞原理和利用方法
- 影响评估：可获得的权限和影响范围
- 修复建议：详细的安全加固方案
- 攻击路径：具体的利用步骤（如适用）
严格标准：必须提供完整的漏洞利用路径和影响分析。
必须使用中文回复。
            """
            output_format = audit_ret_format + "\n\n" + _VULN_XML_FORMAT_ZH

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

        elapsed_time = (time.time() - result_meta["start_time"]) / 60
        logger.info(f"Scan completed, total elapsed time {elapsed_time:.2f} minutes")

        lang_stats = analyze_language(repo_dir)
        top_language = get_top_language(lang_stats)
        safety_score = calc_mcp_score(vuln_results)

        result_meta.update(
            {
                "readme": audit_result,
                "score": safety_score,
                "language": top_language,
                "end_time": time.time(),
                "results": vuln_results,
            }
        )
        mcpLogger.result_update(result_meta)
        return result_meta

    async def _scan_three_stage(
        self, repo_dir: str, prompt: str, language: str, result_meta: dict
    ) -> dict:
        """Three-stage pipeline: Info Collection → Code Audit → Vulnerability Review."""

        # Stage 1: Info Collection
        if language == "en":
            info_ret_format = "Generate a detailed information collection report in Markdown format. The report should be based on input data and summarized faithfully, ensuring readers (who know nothing about the project) can quickly understand the overall picture. You MUST write the entire report in English."
            stage1_name = "Info Collection"
            ctx_key1 = "Info Collection Report"
        else:
            info_ret_format = "生成一份详细的信息收集报告，使用Markdown格式。报告需基于输入数据如实总结，确保读者（对项目一无所知）能快速理解项目全貌。必须使用中文回复。"
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

        # Stage 2: Code Audit
        if language == "en":
            audit_ret_format = """
Return in Markdown format.
For each confirmed vulnerability, you must provide:
- Specific location: file path and line number range
- Complete code snippet: the code segment showing the vulnerability
- Technical analysis: vulnerability principles and exploitation methods
- Impact assessment: privileges and scope that can be obtained
- Remediation suggestions: detailed security hardening plan
- Attack path: specific exploitation steps (if applicable)
Strict criteria: must provide complete vulnerability exploitation paths and impact analysis.
You MUST write the entire report in English.
            """
            stage2_name = "Code Audit"
            ctx_key2 = "Code Audit Report"
        else:
            audit_ret_format = """
markdown格式返回
对于每个确认的漏洞，必须提供：
- 具体位置：文件路径和行号范围
- 完整代码片段：显示漏洞的代码段
- 技术分析：漏洞原理和利用方法
- 影响评估：可获得的权限和影响范围
- 修复建议：详细的安全加固方案
- 攻击路径：具体的利用步骤（如适用）
严格标准：必须提供完整的漏洞利用路径和影响分析。
必须使用中文回复。
            """
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
            review_format = _VULN_XML_FORMAT_EN + _LANGUAGE_DIRECTIVE_EN
            stage3_name = "Vulnerability Review"
            ctx_key3 = "Code Audit Report"
        else:
            review_format = _VULN_XML_FORMAT_ZH
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

        # 提取与分析结果
        extractor = VulnerabilityExtractor()
        vuln_results = extractor.extract_vulnerabilities(vuln_review)

        # Fallback: if extraction fails, use extract_result as a fallback
        if not vuln_results:
            parsed = extract_result(vuln_review)
            if parsed:
                vuln_results = [parsed]

        elasped_time = (time.time() - result_meta["start_time"]) / 60
        logger.info(f"扫描任务完成，总耗时 {elasped_time:.2f} 分钟")
        lang_stats = analyze_language(repo_dir)
        top_language = get_top_language(lang_stats)
        safety_score = calc_mcp_score(vuln_results)

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

    async def dynamic_analysis(self, prompt: str):
        result_meta = {
            "readme": "",
            "score": 0,
            "language": "",
            "start_time": time.time(),
            "end_time": 0,
            "results": [],
        }

        if self.language == "en":
            info_ret_format = "Generate a detailed MCP (Model Context Protocol) information collection report in Markdown format. The report should be based on input data and summarized faithfully, ensuring readers (who know nothing about the project) can quickly understand the overall picture. You MUST write the entire report in English."
            stage1_name = "Info Collection"
            ctx_key1 = "Info Collection Report"
        else:
            info_ret_format = "生成一份详细的MCP(model context protocol)信息收集报告，使用Markdown格式。报告需基于输入数据如实总结，确保读者（对项目一无所知）能快速理解项目全貌。必须使用中文回复。"
            stage1_name = "信息收集"
            ctx_key1 = "信息收集报告"
        info_collection = await self.pipeline.execute_stage_dynamic(
            ScanStage(
                "1",
                stage1_name,
                "agents/dynamic/project_summary",
                output_format=info_ret_format,
                language=self.language,
            ),
            prompt=prompt,
        )
        result_meta["readme"] = info_collection

        # 漏洞探测
        if self.language == "en":
            vuln_ret_format = """
        ## Output format
- The output should be in Markdown format. Please Never use any other format, and make sure the output has no format issue.
- The Markdown document should have the following Chapter:
    - "Overview": `YES` or `NO`, representing whether there are any risks analyzed.
    - "Threats": A list of xml strings, each representing a threat analyzed. Including threat types, confidence scores, and potential impacts.
    - "Reasons": A list of normal strings, each representing the reason why the corresponding threat is analyzed.
    - "Summarization": A paragraph summarizing the overall security assessment results.
- example:
    ```
    # Overview
    - YES
    # Threats
        - <threat><tool_name>{{ tool_name }}</tool_name><type>SQL Injection</type><confidence>0.9</confidence><impact>High</impact></threat>
    # Reasons 
        - SQL Injection: The tool named {{ tool_name }} detected a potential SQL Injection vulnerability in the input parameter.
    # Summarization: 
        ...... (The clear, detailed summary of the security assessment results)
    ```
You MUST write all content in English.
        """
            stage2_name = "Malicious Testing"
            stage3_name = "Vulnerability Testing"
            stage4_name = "Vulnerability Review"
        else:
            vuln_ret_format = """
        ## Output format
- The output should be in Markdown format. Please Never use any other format, and make sure the output has no format issue.
- The Markdown document should have the following Chapter:
    - "Overview": `YES` or `NO`, representing whether there are any risks analyzed.
    - "Threats": A list of xml strings, each representing a threat analyzed. Including threat types, confidence scores, and potential impacts.
    - "Reasons": A list of normal strings, each representing the reason why the corresponding threat is analyzed.
    - "Summarization": A paragraph summarizing the overall security assessment results.
- example:
    ```
    # Overview
    - YES
    # Threats
        - <threat><tool_name>{{ tool_name }}</tool_name><type>SQL Injection</type><confidence>0.9</confidence><impact>High</impact></threat>
    # Reasons 
        - SQL Injection: The tool named {{ tool_name }} detected a potential SQL Injection vulnerability in the input parameter.
    # Summarization: 
        ...... (The clear, detailed summary of the security assessment results)
    ```
必须使用中文回复。
        """
            stage2_name = "恶意行为检测"
            stage3_name = "漏洞检测"
            stage4_name = "漏洞整理"
        report1 = await self.pipeline.execute_stage_dynamic(
            ScanStage(
                "2",
                stage2_name,
                "agents/dynamic/malicious_behaviour_testing.md",
                output_format=vuln_ret_format,
                language=self.language,
            ),
            prompt,
            {ctx_key1: info_collection},
        )
        report2 = await self.pipeline.execute_stage_dynamic(
            ScanStage(
                "3",
                stage3_name,
                "agents/dynamic/vulnerability_testing.md",
                output_format=vuln_ret_format,
                language=self.language,
            ),
            prompt,
            {ctx_key1: info_collection, stage2_name: report1},
        )

        # 3. 漏洞整理
        if self.language == "en":
            review_format = _VULN_XML_FORMAT_EN + _LANGUAGE_DIRECTIVE_EN
        else:
            review_format = _VULN_XML_FORMAT_ZH
        vuln_review = await self.pipeline.execute_stage_dynamic(
            ScanStage(
                "4",
                stage4_name,
                "agents/dynamic/general_analyzing_prompt_template",
                output_format=review_format,
                output_check_fn=is_vuln_review_output,
                language=self.language,
            ),
            prompt,
            {stage2_name: report1, stage3_name: report2},
        )
        # 提取与分析结果
        extractor = VulnerabilityExtractor()
        vuln_results = extractor.extract_vulnerabilities(vuln_review)
        safety_score = calc_mcp_score(vuln_results)

        result_meta.update(
            {
                "readme": info_collection,
                "score": safety_score,
                "end_time": time.time(),
                "results": vuln_results,
            }
        )
        mcpLogger.result_update(result_meta)
        return result_meta
