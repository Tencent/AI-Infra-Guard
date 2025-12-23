import os
import time
from typing import List, Dict, Any, Optional

from agent.base_agent import BaseAgent
from tools.dispatcher import ToolDispatcher
from utils.prompt_manager import prompt_manager
from utils.dynamic_tasks import get_targets_for_tasks
from utils.extract_vuln import VulnerabilityExtractor
from utils.loging import logger
from utils.aig_logger import mcpLogger
from utils.project_analyzer import analyze_language, get_top_language, calc_mcp_score
from utils.parse import parse_mcp_invocations


class ScanStage:
    """定义扫描的一个阶段"""

    def __init__(self, stage_id: str, name: str, template: str, output_format: str = None, output_check_fn=None,
                 next_step_msg: str = None):
        self.stage_id = stage_id
        self.name = name
        self.template = template
        self.output_format = output_format
        self.next_step_msg = next_step_msg
        self.output_check_fn = output_check_fn


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


class Agent:
    def __init__(self, llm, specialized_llms: dict = None, debug: bool = False, dynamic: bool = False,
                 server_url: str = None):
        self.llm = llm
        self.specialized_llms = specialized_llms or {}
        self.debug = debug
        self.dynamic = dynamic
        self.dispatcher = ToolDispatcher(mcp_server_url=server_url)
        self.pipeline = ScanPipeline(self)

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
        info_ret_format = "生成一份详细的代码审计信息收集报告，使用Markdown格式。报告需基于输入数据如实总结，确保读者（对项目一无所知）能快速理解项目全貌。"
        info_collection = await self.pipeline.execute_stage(
            ScanStage("1", "信息收集", "agents/project_summary", output_format=info_ret_format),
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
            ScanStage("2", "代码审计", "agents/code_audit", output_format=audit_ret_format),
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
            ScanStage("3", "漏洞整理", "agents/vuln_review", output_format=review_format,
                      output_check_fn=vuln_review_check),
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

    async def dynamic_analysis(self, repo_dir: str, server_url: str, server_transport: str, tasks: list):
        logger.info("=== 阶段4: 动态分析 ===")
        mcpLogger.new_plan_step(stepId="4", stepName="动态分析")

        # 确保环境变量已设置（Dispatcher 会用到）
        os.environ["MCP_SERVER_URL"] = server_url
        os.environ["MCP_TRANSPORT_PROTOCOL"] = server_transport

        try:
            targets_list = get_targets_for_tasks(tasks or [])
        except Exception as e:
            logger.error(f"动态任务加载失败: {e}")
            raise

        results = []
        for idx, (name, config) in enumerate(targets_list):
            target_prompt = config.get("prompt_content") or ""
            if not target_prompt and config.get("prompt"):
                with open(config["prompt"]) as f:
                    target_prompt = f.read()

            target_type = config.get("type", "malicious")
            logger.info(f"[Dynamic] Start target {name} ({target_type})")

            # 准备 Prompt
            if target_type == "malicious":
                instruction = prompt_manager.load_template("agents/dynamic/malicious_behaviour_testing")
            else:
                instruction = prompt_manager.load_template("agents/dynamic/vulnerability_testing")

            # a. 测试阶段 (注入 MCP 能力)
            testing_agent = BaseAgent(
                name="TestingAgent",
                instruction=instruction,
                llm=self.llm,
                dispatcher=self.dispatcher,
                specialized_llms=self.specialized_llms,
                log_step_id=f"4.{idx + 1}.1",
                debug=self.debug,
                capabilities=["standard", "mcp"]
            )
            testing_agent.set_repo_dir(repo_dir)
            # 注入特定的 target_prompt 变量到 instruction (这里需要微调 generate_system_prompt 或直接在这里处理)
            # 我们在 BaseAgent.generate_system_prompt 中添加了对 target_prompt 的支持逻辑
            testing_agent.instruction += f"\n\n测试目标详情:\n```yaml\n{target_prompt}\n```"

            testing_agent.add_user_message(f"请进行测试用例生成，测试目标: {name}\n类别: {target_type}\n")

            history_summary = await testing_agent.run()

            # 提取 MCP 调用并执行 (这部分逻辑保持在 Agent 层作为协调)
            mcp_calls = parse_mcp_invocations(history_summary) or []
            test_history = []
            for call in mcp_calls:
                # 通过 dispatcher 直接调用远程工具
                try:
                    # 注意：dispatcher.call_tool 是统一接口，这里我们可能需要更详细的信息
                    # 但为了简化架构，我们直接用 dispatcher 的 manager
                    tool_info, execution = await self.dispatcher.mcp_tools_manager.call_remote_tool(call)
                    test_history.append({"tool_info": tool_info, "tool_call": call, "execution_result": execution})
                except Exception as e:
                    logger.error(f"MCP Tool call failed: {e}")

            # b. 分析阶段
            analysis_instr = prompt_manager.load_template("agents/dynamic/general_analyzing_prompt_template")
            analysis_format = "请使用中文输出最终的分析报告，确保包含测试结论、风险等级和修复建议。"
            analyzing_agent = BaseAgent(
                name="AnalyzingAgent",
                instruction=analysis_instr,
                llm=self.llm,
                dispatcher=self.dispatcher,
                specialized_llms=self.specialized_llms,
                log_step_id=f"4.{idx + 1}.2",
                debug=self.debug,
                output_format=analysis_format
            )
            analyzing_agent.add_user_message(
                f"请进行测试用例结果分析，测试历史为{test_history}\n使用中文输出最终的分析报告。")
            execution_review = await analyzing_agent.run()

            results.append({
                "target": name,
                "type": target_type,
                "test_execution": test_history,
                "execution_review": execution_review,
            })

        return results
