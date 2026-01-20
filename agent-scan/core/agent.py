import time
from typing import Dict, Any, Optional

import utils.llm
from core.agent_adapter.adapter import AIProviderClient, ProviderOptions
from core.base_agent import BaseAgent
from utils.aig_logger import mcpLogger
from utils.extract_vuln import VulnerabilityExtractor
from utils.loging import logger
from utils.project_analyzer import analyze_language, get_top_language, calc_mcp_score
from utils.prompt_manager import prompt_manager


class ScanStage:
    """定义扫描的一个阶段"""

    def __init__(self, stage_id: str, name: str, template: str, language="zh"):
        self.stage_id = stage_id
        self.name = name
        self.template = template
        self.language = language


class ScanPipeline:
    """标准扫描流水线逻辑"""

    def __init__(self, agent_wrapper: 'Agent'):
        self.agent_wrapper = agent_wrapper

    async def execute_stage(self, stage: ScanStage, repo_dir: str, prompt: str,
                            agent_provider: ProviderOptions | None = None,
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
            specialized_llms=self.agent_wrapper.specialized_llms,
            log_step_id=stage.stage_id,
            debug=self.agent_wrapper.debug,
            agent_provider=agent_provider,
            language=stage.language
        )
        user_msg = ""
        await agent.initialize()
        if repo_dir:
            agent.set_repo_dir(repo_dir)
            user_msg = f"请进行{stage.name}，文件夹在 {repo_dir}\n{prompt}"
        if context_data:
            user_msg += "\n\n有以下背景信息：\n"
            for key, value in context_data.items():
                user_msg += f"{key}:{value}\n\n"

        agent.add_user_message(user_msg)

        # 运行并返回结果
        result = await agent.run()
        return result


class Agent:
    def __init__(self, llm: utils.llm.LLM, specialized_llms: dict = None, debug: bool = False,
                 language='zh', agent_provider=None):
        self.llm = llm
        self.specialized_llms = specialized_llms or {}
        self.debug = debug
        self.pipeline = ScanPipeline(self)
        self.language = language
        self.agent_provider: ProviderOptions | None = None
        if agent_provider:
            client = AIProviderClient()
            self.agent_provider = client.load_config_from_file(agent_provider)[0]

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
        info_collection = await self.pipeline.execute_stage(
            ScanStage("1", "Info Collection", "project_summary", language=self.language),
            repo_dir, prompt, self.agent_provider
        )

        # 2. 漏洞检测
        code_audit = await self.pipeline.execute_stage(
            ScanStage("2", "Vulnerability Check", "vulnerability_detctor", language=self.language),
            repo_dir, prompt, self.agent_provider, {"信息收集报告": info_collection}
        )

        # 3. 漏洞整理
        vuln_review = await self.pipeline.execute_stage(
            ScanStage("3", "Vulnerability Review", "agent_security_reviewer",
                      language=self.language),
            repo_dir, prompt, self.agent_provider, {"代码审计报告": code_audit}
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
