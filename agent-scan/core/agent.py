import time
from typing import Dict, Any

import utils.llm
from core.agent_adapter.adapter import AIProviderClient, ProviderOptions
from core.base_agent import run_agent
from utils.aig_logger import scanLogger
from utils.logging import logger
from utils.project_analyzer import analyze_language, get_top_language
from utils.prompt_manager import prompt_manager
from core.report import generate_report_from_xml


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
        instruction = prompt_manager.load_template(stage.template)
        return await run_agent(stage.name, instruction, self.agent_wrapper.llm, prompt, stage.stage_id,
                               self.agent_wrapper.specialized_llms,
                               agent_provider, stage.language, repo_dir, context_data)


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

    async def scan(self, repo_dir: str, prompt: str) -> Dict[str, Any]:
        start_time = time.time()

        # 1. 信息收集
        info_collection = await self.pipeline.execute_stage(
            ScanStage("1", "Info Collection", "project_summary", language=self.language),
            repo_dir, prompt, self.agent_provider
        )

        # 2. 漏洞检测 (Agent-focused)
        vuln_detection = await self.pipeline.execute_stage(
            ScanStage("2", "Vulnerability Detection", "agent_vulnerability_detector", language=self.language),
            repo_dir, prompt, self.agent_provider, {"信息收集报告": info_collection}
        )

        # 3. 漏洞整理
        vuln_review = await self.pipeline.execute_stage(
            ScanStage("3", "Vulnerability Review", "agent_security_reviewer",
                      language=self.language),
            repo_dir, prompt, self.agent_provider, {"漏洞检测报告": vuln_detection}
        )

        # 生成标准化报告
        end_time = time.time()
        elapsed_time = (end_time - start_time) / 60
        logger.info(f"扫描任务完成，总耗时 {elapsed_time:.2f} 分钟")

        lang_stats = analyze_language(repo_dir)
        top_language = get_top_language(lang_stats)

        # Generate AgentSecurityReport
        # Extract agent_type from provider configuration
        agent_type = ""
        if self.agent_provider and self.agent_provider.id:
            # Extract provider type from id (e.g., "dify:bot_123" -> "dify", "coze" -> "coze")
            provider_id = self.agent_provider.id
            if ":" in provider_id:
                agent_type = provider_id.split(":")[0]
            else:
                agent_type = provider_id
        
        report = generate_report_from_xml(
            vuln_text=vuln_review,
            agent_name=repo_dir.split('/')[-1] if repo_dir else "",
            agent_type=agent_type,
            model_name=getattr(self.llm, 'model', ''),
            plugins=[],
            start_time=int(start_time),
            end_time=int(end_time),
            report_description=info_collection,
        )

        result = report.dict()
        result["language"] = top_language

        scanLogger.result_update(result)
        return result
