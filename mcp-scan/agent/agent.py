import os
import time
from agent.base_agent import BaseAgent
from agent.dynamic_base_agent import DynamicBaseAgent
from utils.dynamic_tasks import get_targets_for_tasks
from utils.extract_vuln import VulnerabilityExtractor
from utils.loging import logger
from utils.config import base_dir
from utils.aig_logger import *
from utils.project_analyzer import analyze_language, get_top_language, calc_mcp_score
from utils.parse import parse_mcp_invocations



class Agent:

    def __init__(self, llm, specialized_llms: dict = None, debug: bool = False, dynamic: bool = False, server_url: str = None, server_transport: str = "http"):
        self.llm = llm
        self.specialized_llms = specialized_llms or {}
        self.prompt_summary = os.path.join(base_dir, "prompt", "agents", "project_summary.md")
        self.prompt_code_audit = os.path.join(base_dir, "prompt", "agents", "code_audit.md")
        self.prompt_mcp_opera = os.path.join(base_dir, "prompt", "agents", "mcp_opera.md")
        self.prompt_vuln_review = os.path.join(base_dir, "prompt", "agents", "vuln_review.md")
        # self.prompt_build_preview = os.path.join(base_dir, "prompt", "agents", "build_preview.md")
        # self.prompt_dynamic_verification = os.path.join(base_dir, "prompt", "agents", "dynamic_verification.md")
        self.debug = debug
        self.dynamic = dynamic
        self.server_url = server_url
        self.server_transport = server_transport

    def scan(self, repo_dir: str, prompt: str):
        result = {
            "readme": "",
            "score": 0,
            "language": "",
            "start_time": 0,
            "end_time": 0,
            "results": [],
        }
        # 信息收集
        start_time = time.time()
        logger.info("=== 阶段1: 信息收集 ===")
        mcpLogger.new_plan_step(stepId="1", stepName="信息收集")

        with open(self.prompt_summary) as f:
            mcpLogger.status_update("1", "我已收到任务", "", "completed")
            agent = BaseAgent("信息收集Agent", f.read(), self.llm, self.specialized_llms, "1", self.debug)
            agent.set_repo_dir(repo_dir)
            agent.add_user_message(f"请进行信息收集，文件夹在 {repo_dir}\n{prompt}")
            info_collection = agent.run()

        # 代码审计
        logger.info("=== 阶段2: 代码审计 ===")
        mcpLogger.new_plan_step(stepId="2", stepName="代码审计")
        with open(self.prompt_code_audit) as f:
            agent = BaseAgent("代码审计Agent", f.read(), self.llm, self.specialized_llms, "2", self.debug)
            agent.set_repo_dir(repo_dir)
            agent.add_user_message(f"请进行代码审计，文件夹在 {repo_dir}\n{prompt}\n信息收集报告:\n{info_collection}")
            code_audit = agent.run()

        # 漏洞整理
        logger.info("=== 阶段3: 漏洞整理 ===")
        mcpLogger.new_plan_step(stepId="3", stepName="漏洞整理")
        with open(self.prompt_vuln_review) as f:
            agent = BaseAgent("漏洞整理Agent", f.read(), self.llm, self.specialized_llms, "3", self.debug)
            agent.set_repo_dir(repo_dir)
            agent.add_user_message(f"请进行漏洞整理，文件夹在 {repo_dir}\n{prompt}\n代码审计报告:\n{code_audit}")
            vuln_review = agent.run()
            extractor = VulnerabilityExtractor()
            vuln_results = extractor.extract_vulnerabilities(vuln_review)
            logger.info(f"发现 {len(vuln_results)} 个漏洞")
            print(f"\n发现的漏洞:\n{vuln_results}\n")
        elasped_time = time.time() - start_time
        elasped_time = elasped_time / 60
        logger.info(f"漏洞整理完成，耗时 {elasped_time} 分钟")

        # 分析项目语言
        lang_stats = analyze_language(repo_dir)
        top_language = get_top_language(lang_stats)
        logger.info(f"项目主要语言: {top_language}, 统计: {lang_stats}")

        # 计算安全分数
        safety_score = calc_mcp_score(vuln_results)
        logger.info(f"安全评分: {safety_score}/100")

        result["readme"] = info_collection
        result["score"] = safety_score
        result["language"] = top_language
        result["start_time"] = start_time
        result["end_time"] = time.time()
        result["results"] = vuln_results
        mcpLogger.result_update(result)

        # 保存阶段性结果，供 dynamic_analysis 使用（如果后续以单独命令调用）
        self._info_collection = info_collection
        self._code_audit = code_audit
        self._vuln_review = vuln_review
        return {
            "info_collection": info_collection,
            "vuln_review": vuln_review,
            "vuln_count": len(vuln_results),
        }

    async def dynamic_analysis(
            self,
            repo_dir: str,
            server_url: str,
            server_transport,
            tasks: list,
        ):
        logger.info("=== 阶段4: 动态分析 ===")
        mcpLogger.new_plan_step(stepId="4", stepName="动态分析")

        # 1. 把 server_url 暴露到环境，供 DynamicBaseAgent 读取
        if server_url:
            import os as _os
            _os.environ.setdefault("MCP_SERVER_URL", server_url)
            _os.environ.setdefault("MCP_TRANSPORT_PROTOCOL", server_transport)
        else:
            raise ValueError("MCP server URL is required for dynamic analysis.")
        
        # 2. 根据传入的任务名，从配置中按顺序获取 targets
        try:
            targets_list = get_targets_for_tasks(tasks or [])
        except Exception as e:
            logger.error(f"动态任务加载失败: {e}")
            raise

        def load_prompt(path):
            with open(path) as f:
                return f.read()

        results = []

        # 3. 依次执行每个 target 的测试和分析
        for idx, (name, config) in enumerate(targets_list):
            target_prompt = load_prompt(config["prompt"]) if config.get("prompt") else ""
            target_type = config.get("type", "malicious")

            logger.info(f"[Dynamic] Start target {name} ({target_type})")

            if target_type == "malicious":
                instruction_prompt_path = os.path.join(base_dir, "prompt", "agents","dynamic", "malicious_behaviour_testing.md")
            else:
                instruction_prompt_path = os.path.join(base_dir, "prompt", "agents", "dynamic", "vulnerability_testing.md")
            analysis_prompt_path = os.path.join(base_dir, "prompt", "agents","dynamic", "general_analyzing_prompt_template.md")
            instruction_prompt=load_prompt(instruction_prompt_path)
            analysis_prompt=load_prompt(analysis_prompt_path)

            # a. 测试
            testing_agent = DynamicBaseAgent(
                "TestingAgent", instruction_prompt, target_prompt,
                self.llm, self.specialized_llms,
                f"4.{idx+1}.1", self.debug, "test"
            )
            await testing_agent.generate_system_prompt()
            testing_agent.set_repo_dir(repo_dir)
            testing_agent.add_user_message(
                f"请进行测试用例生成，测试目标: {name}\n类别: {target_type}\n"
            )
            # 对每个target会生成若干测试用例；
            # 对测试用例的List进行提取后，逐个执行，并收集结果。
            
            remote_tool_call_response = testing_agent.run()
            logger.info(f"[Dynamic] Tool call response received")
            logger.debug(f"[Dynamic] Tool call response content: {remote_tool_call_response}")

            remote_tool_calls = parse_mcp_invocations(remote_tool_call_response)
            logger.info(f"[Dynamic] Extracted tool calls: {remote_tool_calls}")
            test_history = []
            for call in remote_tool_calls:
                logger.info(f"[Dynamic] Executing tool call: {call}")
                # call_remote_tool is async; await it
                tool_info, test_execution = await testing_agent.call_remote_tool(call)
                tool_call_item = {
                    "tool_info": tool_info,
                    "tool_call": call,
                    "execution_result": test_execution,
                }
                logger.info(f"[Dynamic] Tool call executed, result: {tool_call_item}")
                test_history.append(tool_call_item)
        

            # b. 分析
            analyzing_agent = DynamicBaseAgent(
                "AnalyzingAgent", analysis_prompt, target_prompt,
                self.llm, self.specialized_llms,
                f"4.{idx+1}.2", self.debug, "analyze"
            )
            await analyzing_agent.generate_system_prompt()
            analyzing_agent.set_repo_dir(repo_dir)
            analyzing_agent.add_user_message(
                f"请进行测试用例结果分析，测试历史为{test_history}\n使用中文输出最终的分析报告。"
            )
            execution_review = analyzing_agent.run()

            results.append({
                "target": name,
                "type": target_type,
                "test_execution": test_history,
                "execution_review": execution_review,
            })

        return results

