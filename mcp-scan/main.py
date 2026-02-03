#!/usr/bin/env python3
"""
Agent Framework - 主入口文件

这是一个模仿 Claude Code / Gemini CLI 的 Agent 框架。
Agent 可以自动调用工具完成任务。
"""
import asyncio
import os
import sys
import argparse
from agent.agent import Agent
from utils.llm import LLM
# 配置专用模型
from utils.llm_manager import LLMManager
from utils.loging import logger
from utils.aig_logger import mcpLogger
from utils import config

# 重要：导入 tools 包以触发工具注册
import tools as _


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Agent Framework - 代码扫描和漏洞检测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 必需参数
    parser.add_argument(
        "--repo",
        default="",
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
        "--server_url",
        help=f"remote MCP server URL",
        default=None
    )

    parser.add_argument(
        "--header",
        action="append",
        dest="headers",
        help="Custom header in key:value format (can be used multiple times)",
        default=[]
    )

    parser.add_argument("--language", default="zh", help="Output language (zh/en)")

    return parser.parse_args()


async def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()

    # 获取 API Key（优先使用命令行参数，否则从环境变量读取）
    api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("API Key not provided. Use --api-key or set OPENROUTER_API_KEY environment variable.")
        sys.exit(1)


    # 创建主 LLM 实例
    llm = LLM(model=args.model, api_key=api_key, base_url=args.base_url)
    logger.info(f"Main LLM initialized: {args.model}")

    # 使用主 API Key 作为默认值
    llm_manager = LLMManager(api_key=api_key, base_url=args.base_url)

    # 获取专用LLM实例字典
    specialized_llms = llm_manager.get_specialized_llms(["thinking", "coding"])
    logger.info(f"Specialized LLMs configured: {list(specialized_llms.keys())}")

    # 创建 Agent 实例，传入专用模型

    logger.info(f"Starting scan on: {args.repo}")
    prompt = args.prompt
    if args.language == "en":
        prompt += "All responses should be in English."
    elif args.language == "zh":
        prompt += "所有回复都应使用中文。"
    if prompt:
        logger.info(f"Custom prompt: {prompt}")

    # 解析 headers
    headers = {}
    if args.headers:
        for header_item in args.headers:
            try:
                if ':' in header_item:
                    key, value = header_item.split(':', 1)
                    headers[key.strip()] = value.strip()
                elif '=' in header_item:
                    key, value = header_item.split('=', 1)
                    headers[key.strip()] = value.strip()
                else:
                    logger.warning(f"Ignored invalid header format: {header_item}")
            except Exception as e:
                logger.warning(f"Failed to parse header {header_item}: {e}")
        
        if headers:
            logger.info(f"Custom headers: {headers}")

    agent = Agent(llm=llm, specialized_llms=specialized_llms, debug=args.debug, server_url=args.server_url,
                  language=args.language, headers=headers)
    try:
        if args.server_url:
            logger.info(f"Server mode enabled with URL: {args.server_url}")
            dynamic_results = await agent.dynamic_analysis(prompt)
            logger.info(f"Dynamic analysis results:\n{dynamic_results}")
        else:
            # 验证项目路径
            if not os.path.exists(args.repo):
                logger.error(f"Project path does not exist: {args.repo}")
                sys.exit(1)

            if not os.path.isdir(args.repo):
                logger.error(f"Project path is not a directory: {args.repo}")
                sys.exit(1)
            result = await agent.scan(args.repo, prompt)
            logger.info(f"Scan completed successfully:\n\n {result}")
    except KeyboardInterrupt:
        print("\n\nTask interrupted by user.")
        logger.warning("Task interrupted by user")
    except Exception as e:
        print(f"\n\nError during execution: {e}")
        logger.error(f"Error during execution: {e}")
        import traceback
        traceback = traceback.format_exc()
        mcpLogger.error_log(f"Execution failed: {e}\n{traceback}")
        raise e
    finally:
        # 确保关闭资源
        if hasattr(agent, 'dispatcher'):
            await agent.dispatcher.close()


if __name__ == "__main__":
    # 先解析参数以检查是否为 debug 模式
    args = parse_args()
    # 如果是 debug 模式，初始化 Laminar
    asyncio.run(main())
