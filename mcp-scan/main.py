#!/usr/bin/env python3
"""
Agent Framework - 主入口文件

这是一个模仿 Claude Code / Gemini CLI 的 Agent 框架。
Agent 可以自动调用工具完成任务。
"""
import logging
import os
import sys
import argparse
from agent.base_agent import BaseAgent
from agent.agent import Agent
from utils.dynamic_tasks import get_allowed_dynamic_tasks
from utils.llm import LLM
from utils.loging import logger
from utils import config
from lmnr import Laminar

# 重要：导入 tools 包以触发工具注册
import tools


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Agent Framework - 代码扫描和漏洞检测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 必需参数
    parser.add_argument(
        "repo",
        help="要扫描的项目文件夹路径"
    )

    # 可选参数
    parser.add_argument(
        "-p", "--prompt",
        default="",
        help="自定义扫描提示词（可选）"
    )

    parser.add_argument(
        "-m", "--model",
        default=config.DEFAULT_MODEL,
        help=f"LLM 模型名称（默认: {config.DEFAULT_MODEL}）"
    )

    parser.add_argument(
        "-k", "--api_key",
        default=None,
        help="API Key（如果不提供，将从环境变量 OPENROUTER_API_KEY 读取）"
    )

    parser.add_argument(
        "-u", "--base_url",
        default=config.DEFAULT_BASE_URL,
        help=f"API 基础 URL（默认: {config.DEFAULT_BASE_URL}）"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用 debug 模式（包括 Laminar 跟踪）",
        default=False,
    )

    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="启用动态分析模式（需要指定 MCP 服务器 URL）",
        default=False,
    )

    parser.add_argument(
        "-t", "--tasks",
        nargs="+",
        help="动态分析要执行的任务列表（空格分隔），例如: -t test analyze",
        default=None
    )

    parser.add_argument(
        "--server_url",
        help=f"remote MCP server URL",
        default=None
    )

    parser.add_argument(
        "--server_transport",
        help=f"remote MCP server transport protocol",
        default="streamable-http"
    )
    return parser.parse_args()

def task_validation(input_tasks: list) -> bool:
    """验证任务列表是否合法"""
    if not input_tasks or len(input_tasks) == 0:
        logger.error("动态模式需要通过 --tasks 指定至少一个任务")
        return False
    try:
        allowed_tasks = get_allowed_dynamic_tasks()
    except Exception:
        logger.error("无法获取允许的动态任务列表，请检查配置文件是否正确")
        return False
    invalid_tasks = [t for t in input_tasks if t not in allowed_tasks]
    if invalid_tasks:
        logger.error(f"无效的任务: {invalid_tasks}。允许的任务: {allowed_tasks}")
        return False
    return True


async def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()

    # 获取 API Key（优先使用命令行参数，否则从环境变量读取）
    api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("API Key not provided. Use --api-key or set OPENROUTER_API_KEY environment variable.")
        sys.exit(1)

    # 验证项目路径
    if not os.path.exists(args.repo):
        logger.error(f"Project path does not exist: {args.repo}")
        sys.exit(1)

    if not os.path.isdir(args.repo):
        logger.error(f"Project path is not a directory: {args.repo}")
        sys.exit(1)

    # 创建主 LLM 实例
    llm = LLM(model=args.model, api_key=api_key, base_url=args.base_url)
    logger.info(f"Main LLM initialized: {args.model}")

    # 配置专用模型
    from utils.llm_manager import LLMManager

    # 使用主 API Key 作为默认值
    llm_manager = LLMManager(api_key=api_key, base_url=args.base_url)

    # 获取专用LLM实例字典
    specialized_llms = llm_manager.get_specialized_llms(["thinking", "coding"])
    logger.info(f"Specialized LLMs configured: {list(specialized_llms.keys())}")

    # 创建 Agent 实例，传入专用模型
    agent = Agent(llm=llm, specialized_llms=specialized_llms, debug=args.debug,
                   dynamic=args.dynamic, server_url=args.server_url)

    logger.info(f"Starting scan on: {args.repo}")
    if args.prompt:
        logger.info(f"Custom prompt: {args.prompt}")    
    try:
        # result = agent.scan(args.repo, args.prompt)
        # logger.info(f"Scan completed successfully:\n\n {result}")

        if args.dynamic:
            logger.info(f"Dynamic analysis enabled with server URL: {args.server_url}")
            if not task_validation(args.tasks):
                raise ValueError("Invalid tasks provided for dynamic analysis.")
            if args.server_transport not in ["streamable-http", "sse"]:
                logger.error(f"Invalid server transport protocol: {args.server_transport}. Allowed values are 'streamable-http' or 'sse'.")
                raise ValueError("Invalid server transport protocol provided for dynamic analysis.")
            dynamic_results = await agent.dynamic_analysis(args.repo, args.server_url, args.server_transport, args.tasks)
            logger.info(f"Dynamic analysis results:\n{dynamic_results}")
    except KeyboardInterrupt:
        print("\n\nTask interrupted by user.")
        logger.warning("Task interrupted by user")
    except Exception as e:
        print(f"\n\nError during execution: {e}")
        logger.error(f"Error during execution: {e}", exc_info=True)
        raise Exception(f"Execution failed: {e}")
    

# Example for dynamic testing & analyzing: `python main.py testcase --dynamic -t tool_poisoning --server_url http://localhost:9005/sse --server_transport sse`
if __name__ == "__main__":
    # 先解析参数以检查是否为 debug 模式
    args = parse_args()

    # 如果是 debug 模式，初始化 Laminar
    console_handler = logging.StreamHandler()
    if args.debug:
        console_handler.setLevel(logging.DEBUG)
        try:
            laminar_key = config.LAMINAR_API_KEY
            if laminar_key:
                Laminar.initialize(project_api_key=laminar_key)
                logger.info("Debug mode enabled - Laminar tracking active")
            else:
                logger.warning("Debug mode enabled but LAMINAR_API_KEY not set")
        except Exception as e:
            logger.warning(f"Failed to initialize Laminar: {e}")
    else:
        console_handler.setLevel(logging.INFO)
    import asyncio
    asyncio.run(main())
