import os
import time
from typing import List, Dict, Any, Optional

from core.base_agent import BaseAgent
from tools.dispatcher import ToolDispatcher
from utils.prompt_manager import prompt_manager
from utils.extract_vuln import VulnerabilityExtractor
from utils.loging import logger
from utils.aig_logger import mcpLogger
from utils.project_analyzer import analyze_language, get_top_language, calc_mcp_score
from utils.parse import parse_mcp_invocations


class ScanStage:
    """定义扫描的一个阶段"""

    def __init__(self, stage_id: str, name: str, template: str, output_format: str = None, output_check_fn=None
                 , language="zh"):
        self.stage_id = stage_id
        self.name = name
        self.template = template
        self.output_format = output_format
        self.output_check_fn = output_check_fn
        self.language = language


class ScanPipeline:
    """标准扫描流水线逻辑"""

    def __init__(self, agent_wrapper: 'Agent'):
        self.agent_wrapper = agent_wrapper
        self.results = {}

    async def execute_stage(self, stage: ScanStage, repo_dir: str, prompt: str,
                            context_data: Dict[str, Any] = None) -> str:
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
            language=stage.language
        )
        agent.set_repo_dir(repo_dir)
        await agent.initialize()

        # 构造用户消息
        user_msg = f"请进行{stage.name}，文件夹在 {repo_dir}\n{prompt}"
        if context_data:
            user_msg += "\n\n有以下背景信息：\n"
            for key, value in context_data.items():
                user_msg += f"{key}:{value}\n\n"

        agent.add_user_message(user_msg)

        # 运行并返回结果
        result = await agent.run()
        self.results[stage.name] = result
        return result

    async def execute_stage_dynamic(self, stage: ScanStage, prompt: str,
                                    context_data: Dict[str, Any] = None) -> str:
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

        # 构造用户消息
        user_msg = f"请进行{stage.name}，进行MCP动态扫描\n{prompt}"
        if context_data:
            user_msg += "\n\n有以下背景信息：\n"
            for key, value in context_data.items():
                user_msg += f"{key}:{value}\n\n"

        agent.add_user_message(user_msg)

        # 运行并返回结果
        result = await agent.run()
        self.results[stage.name] = result
        return result


class Agent:
    def __init__(self, llm, specialized_llms: dict = None, debug: bool = False,
                 server_url: str = None, language='zh', headers=None):
        self.llm = llm
        self.specialized_llms = specialized_llms or {}
        self.debug = debug
        self.dispatcher = ToolDispatcher(mcp_server_url=server_url, mcp_headers=headers)
        self.pipeline = ScanPipeline(self)
        self.language = language

    async def scan(self, repo_dir: str, prompt: str):
        result_meta = {
            "readme": "",
            "score": 0,
            "language": "",
            "start_time": time.time(),
            "end_time": 0,
            "results": [],
        }
        # 1. 信息收集
        info_ret_format = "生成一份详细的信息收集报告，使用Markdown格式。报告需基于输入数据如实总结，确保读者（对项目一无所知）能快速理解项目全貌。"
        info_collection = await self.pipeline.execute_stage(
            ScanStage("1", "Info Collection", "agents/project_summary", output_format=info_ret_format,
                      language=self.language),
            repo_dir, prompt
        )

        # 2. 代码审计
        audit_ret_format = '''
markdown格式返回
对于每个确认的漏洞，必须提供：
- 具体位置：文件路径和行号范围
- 完整代码片段：显示漏洞的代码段
- 技术分析：漏洞原理和利用方法
- 影响评估：可获得的权限和影响范围
- 修复建议：详细的安全加固方案
- 攻击路径：具体的利用步骤（如适用）
严格标准：必须提供完整的漏洞利用路径和影响分析。
        '''
        code_audit = await self.pipeline.execute_stage(
            ScanStage("2", "Code Audit", "agents/code_audit", output_format=audit_ret_format, language=self.language),
            repo_dir, prompt, {"信息收集报告": info_collection}
        )

        # 3. 漏洞整理
        review_format = '''
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
'''.strip()
        vuln_review_check = lambda x: '<vuln>' in x or '<empty>' in x
        vuln_review = await self.pipeline.execute_stage(
            ScanStage("3", "Vulnerability Review", "agents/vuln_review", output_format=review_format,
                      output_check_fn=vuln_review_check, language=self.language),
            repo_dir, prompt, {"代码审计报告": code_audit}
        )

        # 提取与分析结果
        extractor = VulnerabilityExtractor()
        vuln_results = extractor.extract_vulnerabilities(vuln_review)

        elasped_time = (time.time() - result_meta["start_time"]) / 60
        logger.info(f"扫描任务完成，总耗时 {elasped_time:.2f} 分钟")
        lang_stats = analyze_language(repo_dir)
        top_language = get_top_language(lang_stats)
        safety_score = calc_mcp_score(vuln_results)

        result_meta.update({
            "readme": info_collection,
            "score": safety_score,
            "language": top_language,
            "end_time": time.time(),
            "results": vuln_results
        })
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

        info_ret_format = "生成一份详细的MCP(model context protocol)信息收集报告，使用Markdown格式。报告需基于输入数据如实总结，确保读者（对项目一无所知）能快速理解项目全貌。"
        info_collection = await self.pipeline.execute_stage_dynamic(
            ScanStage("1", "Info Collection", "agents/dynamic/project_summary", output_format=info_ret_format,
                      language=self.language),
            prompt=prompt
        )
        result_meta["readme"] = info_collection

        # 漏洞探测
        vuln_ret_format = '''
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
        '''
        report1 = await self.pipeline.execute_stage_dynamic(
            ScanStage("2", "Malicious Testing", "agents/dynamic/malicious_behaviour_testing.md",
                      output_format=vuln_ret_format, language=self.language),
            prompt, {"信息收集报告": info_collection}
        )
        report2 = await self.pipeline.execute_stage_dynamic(
            ScanStage("3", "Vulnerability Testing", "agents/dynamic/vulnerability_testing.md",
                      output_format=vuln_ret_format, language=self.language),
            prompt, {"信息收集报告": info_collection, "malicious testing": report1}
        )

        # 3. 漏洞整理
        review_format = '''
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
        '''.strip()
        vuln_review_check = lambda x: '<vuln>' in x or '<empty>' in x
        vuln_review = await self.pipeline.execute_stage_dynamic(
            ScanStage("4", "Vulnerability Review", "agents/dynamic/general_analyzing_prompt_template",
                      output_format=review_format,
                      output_check_fn=vuln_review_check, language=self.language),
            prompt, {"malicious testing": report1, "vulnerability testing": report2}
        )
        # 提取与分析结果
        extractor = VulnerabilityExtractor()
        vuln_results = extractor.extract_vulnerabilities(vuln_review)
        safety_score = calc_mcp_score(vuln_results)

        result_meta.update({
            "readme": info_collection,
            "score": safety_score,
            "end_time": time.time(),
            "results": vuln_results
        })
        mcpLogger.result_update(result_meta)
        return result_meta
