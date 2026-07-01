#!/usr/bin/env python3
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

"""
Skill-Scan - AI Native Agent Skill 安全审计工具
"""

import argparse
import asyncio
import os
import sys

from agent.agent import Agent
from utils import config
from utils.aig_logger import mcpLogger
from utils.llm import LLM
from utils.llm_manager import LLMManager
from utils.loging import logger

# 重要：导入 tools 包以触发工具注册
import tools as _  # isort: skip

_prompts = {"zh": "所有回复都应使用中文。", "en": "All responses should be in English."}


def resolve_runtime_override(args) -> tuple:
    """解析命令行或环境变量中的 LLM 覆盖配置。

    Returns:
        (api_key, model, base_url) 三元组
    """
    api_key = (
        args.api_key
        or os.getenv("LLM_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
    )
    model = (
        args.model
        or os.getenv("LLM_MODEL", "").strip()
        or os.getenv("OPENAI_MODEL", "").strip()
    )
    base_url = (
        args.base_url
        or os.getenv("LLM_BASE_URL", "").strip()
        or os.getenv("OPENAI_BASE_URL", "").strip()
    )

    return api_key, model, base_url


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Skill-Scan - Agent Skill 安全审计工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 必需参数
    parser.add_argument("--repo", default="", help="要扫描的 Skill 项目文件夹路径")

    # 可选参数
    parser.add_argument("-p", "--prompt", default="", help="自定义扫描提示词（可选）")

    parser.add_argument(
        "-m",
        "--model",
        default=config.DEFAULT_MODEL,
        help=f"LLM 模型名称（默认: {config.DEFAULT_MODEL}）",
    )

    parser.add_argument(
        "-k",
        "--api_key",
        default=None,
        help="API Key（如果不提供，将从环境变量读取）",
    )

    parser.add_argument(
        "-u",
        "--base_url",
        default=config.DEFAULT_BASE_URL,
        help=f"API 基础 URL（默认: {config.DEFAULT_BASE_URL}）",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用 debug 模式",
        default=False,
    )

    parser.add_argument(
        "--language",
        default="zh",
        choices=["zh", "en"],
        help="输出语言: zh(中文,默认) 或 en(英文)",
    )

    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_args()

    override_api_key, override_model, override_base_url = (
        resolve_runtime_override(args)
    )

    api_key = override_api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.error(
            "API Key not provided. Use --api_key or set OPENROUTER_API_KEY environment variable."
        )
        sys.exit(1)

    model = override_model or config.DEFAULT_MODEL
    base_url = override_base_url or config.DEFAULT_BASE_URL

    # 创建主 LLM 实例
    llm = LLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        context_window=config.DEFAULT_MODEL_CONTEXT_WINDOW,
    )
    logger.info(f"Main LLM initialized: {model}")

    # 使用主 API Key 作为默认值
    llm_manager = LLMManager(api_key=api_key, base_url=base_url)
    specialized_llms = llm_manager.get_specialized_llms(["thinking", "coding"])
    logger.info(f"Specialized LLMs configured: {list(specialized_llms.keys())}")

    user_prompt = args.prompt.strip()
    lang_prompt = _prompts.get(args.language, "")
    prompt = f"{user_prompt}\n\n{lang_prompt}" if user_prompt else lang_prompt
    if prompt:
        logger.info(f"Custom prompt: {prompt}")

    agent = Agent(
        llm=llm,
        specialized_llms=specialized_llms,
        debug=args.debug,
        language=args.language,
    )
    try:
        # 验证项目路径
        if not os.path.exists(args.repo):
            logger.error(f"Project path does not exist: {args.repo}")
            sys.exit(1)

        if not os.path.isdir(args.repo):
            logger.error(f"Project path is not a directory: {args.repo}")
            sys.exit(1)

        logger.info(f"Starting scan on: {args.repo}")
        result = await agent.scan(args.repo, prompt, args.language)
        logger.info(f"Scan completed successfully:\n\n {result}")
    except KeyboardInterrupt:
        print("\n\nTask interrupted by user.")
        logger.warning("Task interrupted by user")
    except Exception as e:
        print(f"\n\nError during execution: {e}")
        logger.error(f"Error during execution: {e}")
        import traceback

        tb = traceback.format_exc()
        mcpLogger.error_log(f"Execution failed: {e}\n{tb}")
        raise
    finally:
        if hasattr(agent, "dispatcher"):
            await agent.dispatcher.close()


if __name__ == "__main__":
    asyncio.run(main())
