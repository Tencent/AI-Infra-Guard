import os
import time

from agent.base_agent import BaseAgent
from utils.extract_vuln import VulnerabilityExtractor
from utils.loging import logger
from utils.config import base_dir
from utils.aig_logger import *
from utils.project_analyzer import analyze_language, get_top_language, calc_mcp_score


class Agent:

    def __init__(self, llm, specialized_llms: dict = None, language: str = 'zh', debug: bool = False):
        self.llm = llm
        self.specialized_llms = specialized_llms or {}
        self.prompt_summary = os.path.join(base_dir, "prompt", "agents", "project_summary.md")
        self.prompt_code_audit = os.path.join(base_dir, "prompt", "agents", "code_audit.md")
        self.prompt_mcp_opera = os.path.join(base_dir, "prompt", "agents", "mcp_opera.md")
        self.prompt_vuln_review = os.path.join(base_dir, "prompt", "agents", "vuln_review.md")
        self.prompt_build_preview = os.path.join(base_dir, "prompt", "agents", "build_preview.md")
        self.prompt_dynamic_verification = os.path.join(base_dir, "prompt", "agents", "dynamic_verification.md")
        self.language = language
        self.debug = debug

    def scan(self, repo_dir: str, prompt: str):
        result = {
            "readme": "",
            "score": 0,
            "language": "",
            "start_time": 0,
            "end_time": 0,
            "results": [],
        }
        stepNames = ["信息收集", "代码审计", "漏洞整理"]
        stepNamesEn = ["Info Collection", "Code Audit", "Vulnerability Review"]
        if self.language == 'en':
            stepNames = stepNamesEn
        # 信息收集
        start_time = time.time()
        logger.info("=== 阶段1: 信息收集 ===")
        mcpLogger.new_plan_step(stepId="1", stepName=stepNames[0])
        startDescript = "我已收到任务"
        if self.language == 'en':
            startDescript = "I have received the task"
        with open(self.prompt_summary) as f:
            mcpLogger.status_update("1", startDescript, "", "completed")
            agent = BaseAgent("信息收集Agent", f.read(), self.llm, self.specialized_llms, "1", self.language,
                              self.debug, repo_dir)
            agent.add_user_message(f"请进行信息收集，文件夹在 {repo_dir}\n{prompt}")
            info_collection = agent.run()

        # 代码审计
        logger.info("=== 阶段2: 代码审计 ===")
        mcpLogger.new_plan_step(stepId="2", stepName=stepNames[1])
        with open(self.prompt_code_audit) as f:
            agent = BaseAgent("代码审计Agent", f.read(), self.llm, self.specialized_llms, "2", self.language,
                              self.debug, repo_dir)
            agent.add_user_message(f"请进行代码审计，文件夹在 {repo_dir}\n{prompt}\n信息收集报告:\n{info_collection}")
            code_audit = agent.run()

        # 漏洞整理
        logger.info("=== 阶段3: 漏洞整理 ===")
        mcpLogger.new_plan_step(stepId="3", stepName=stepNames[2])
        with open(self.prompt_vuln_review) as f:
            agent = BaseAgent("漏洞整理Agent", f.read(), self.llm, self.specialized_llms, "3", self.language,
                              self.debug, repo_dir)
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

        # 构建预览
        # logger.info("=== 阶段4: 构建预览 ===")
        # with open(self.prompt_build_preview) as f:
        #     agent = BaseAgent("构建预览Agent", f.read(), self.llm, self.specialized_llms)
        #     agent.add_user_message(f"请进行构建预览，文件夹在 {repo_dir}\n{prompt}\n信息收集报告:\n{info_collection}")
        #     build_preview = agent.run()
        #     logger.info("构建预览完成")
        #     print(f"\n构建预览结果:\n{build_preview}\n")

        # 动态验证
        # logger.info("=== 阶段5: 动态验证 ===")
        # with open(self.prompt_dynamic_verification) as f:
        #     agent = BaseAgent("动态验证Agent", f.read(), self.llm, self.specialized_llms)
        #     # 构造验证任务消息
        #     verification_message = f"""请进行漏洞动态验证。
        # ## 目标仓库
        # {repo_dir}
        #
        # ## 漏洞数据
        # 发现 {len(vuln_results)} 个漏洞需要验证：
        # {vuln_review}
        #
        # ## 服务器部署信息
        # {build_preview}
        #
        # ## 代码审计详情
        # {code_audit}
        #
        # ## 任务要求
        # {prompt}
        #
        # 请按照提示词要求，逐个验证漏洞的可利用性，生成exploit代码并执行验证。
        # """
        #             agent.add_user_message(verification_message)
        #             verification_result = agent.run()
        #             logger.info("动态验证完成")
        #             print(f"\n动态验证结果:\n{verification_result}\n")
        #
        # 返回完整结果
        return {
            "info_collection": info_collection,
            "vuln_review": vuln_review,
            "vuln_count": len(vuln_results),
            # "build_preview": build_preview,
            # "verification_result": verification_result
        }
