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

from agent.base_agent import BaseAgent
from tools.dispatcher import ToolDispatcher
from utils.aig_logger import mcpLogger
from utils.extract_vuln import VulnerabilityExtractor, extract_result
from utils.loging import logger
from utils.pre_scan import pre_scan
from utils.project_analyzer import analyze_language, calc_skill_score, get_top_language
from utils.prompt_manager import prompt_manager

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
    """检查目录是否为空或只含操作系统元数据文件"""
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
    """生成 repo 目录树字符串，直接注入初始提示词"""
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


# SkillTrustBench T01-T09 漏洞分类表 — skill-scan 专属审计内核
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
    """检查输出是否包含合法的 <vuln> XML 结构或 <empty> 标记"""
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
        language: str = "zh",
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
        """执行单个扫描阶段。

        Args:
            stage: 阶段定义
            repo_dir: 项目目录
            prompt: 用户自定义提示词
            context_data: 上游阶段的背景信息
            inject_repo_tree: 是否注入目录树（Stage 2 需要）
            inject_pre_scan: 是否注入静态预扫描结果（Stage 2 需要）
        """
        logger.info(f"=== 阶段 {stage.stage_id}: {stage.name} ===")
        mcpLogger.new_plan_step(stepId=stage.stage_id, stepName=stage.name)

        # 加载提示词模板
        instruction = prompt_manager.load_template(stage.template)

        # 英文指令追加
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

        # 构造用户消息
        user_msg = f"请进行{stage.name}，项目文件夹在 {repo_dir}\n{prompt}"

        if inject_repo_tree:
            repo_tree = _build_repo_tree(repo_dir)
            user_msg += f"\n\n以下是该项目的完整目录结构，供你参考：\n```\n{repo_tree}\n```"

        if inject_pre_scan:
            pre_scan_hints = pre_scan(repo_dir)
            if pre_scan_hints:
                user_msg += f"\n\n{pre_scan_hints}"

        if context_data:
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
    """skill-scan 主 Agent，三阶段流水线入口。"""

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
        """三阶段安全审计流水线。

        Stage 1: Info Collection — 信息收集（SKILL.md 元数据、工具定义、依赖、入口脚本）
        Stage 2: Code Audit — 代码审计（SkillTrustBench T01-T09 内核）
        Stage 3: Vulnerability Review — 漏洞整理（输出 <vuln> XML）
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

        # 空项目检测：直接返回 normal，避免 Agent 对空目录产生幻觉
        if _is_empty_or_metadata_only(repo_dir):
            logger.info("项目为空或仅含系统元数据文件，跳过 LLM 扫描，返回 normal")
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
        info_ret_format = (
            "生成详细的信息收集报告，Markdown格式，基于输入数据如实总结。"
            "报告需包含：项目概述、SKILL.md 元数据分析、工具/脚本清单、依赖与资源、"
            "技术分析（语言/框架/入口）、安全评估（权限需求/网络暴露面）。"
        )
        info_collection = await self.pipeline.execute_stage(
            ScanStage(
                "1",
                "Info Collection",
                "agents/project_summary",
                output_format=info_ret_format,
                language=language,
            ),
            repo_dir,
            prompt,
        )

        # Stage 2: Code Audit — 复用 SkillTrustBench T01-T09 内核
        audit_ret_format = _OUTPUT_FORMAT
        if language == "en":
            audit_ret_format = _OUTPUT_FORMAT + _LANGUAGE_DIRECTIVE_EN
        code_audit = await self.pipeline.execute_stage(
            ScanStage(
                "2",
                "Code Audit",
                "agents/code_audit",
                output_format=audit_ret_format,
                language=language,
            ),
            repo_dir,
            prompt,
            {"信息收集报告": info_collection},
            inject_repo_tree=True,
            inject_pre_scan=True,
        )

        # Stage 3: Vulnerability Review
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
""".strip()
        if language == "en":
            review_format += _LANGUAGE_DIRECTIVE_EN

        vuln_review = await self.pipeline.execute_stage(
            ScanStage(
                "3",
                "Vulnerability Review",
                "agents/vuln_review",
                output_format=review_format,
                output_check_fn=is_vuln_review_output,
                language=language,
            ),
            repo_dir,
            prompt,
            {"代码审计报告": code_audit},
        )

        # 提取结果 + 算分
        extractor = VulnerabilityExtractor()
        vuln_results = extractor.extract_vulnerabilities(vuln_review)

        # 兜底：如果提取失败，使用 extract_result 作为 fallback
        if not vuln_results:
            parsed = extract_result(vuln_review)
            if parsed:
                vuln_results = [parsed]

        elapsed_time = (time.time() - result_meta["start_time"]) / 60
        logger.info(f"扫描任务完成，总耗时 {elapsed_time:.2f} 分钟")

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
