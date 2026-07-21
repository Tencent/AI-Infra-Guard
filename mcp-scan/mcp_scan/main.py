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

"""aig-mcp-scan CLI entry point.

Can be run either as a module (``python -m mcp_scan``) or as a console
script (``aig-mcp-scan``); also exposes the :func:`main` async entry point
for programmatic use.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from mcp_scan import __version__ as _AIG_MCP_SCAN_VERSION
from mcp_scan.agent.agent import Agent
from mcp_scan.utils import config
from mcp_scan.utils.aig_logger import mcpLogger
from mcp_scan.utils.llm import LLM
from mcp_scan.utils.llm_manager import LLMManager
from mcp_scan.utils.loging import logger
from mcp_scan.utils.sarif_formatter import to_sarif

# Important: import the tools package to trigger tool registration
import mcp_scan.tools as _  # isort: skip

_prompts = {"zh": "所有回复都应使用中文。", "en": "All responses should be in English."}

_BANNER = """\
============================================================
  aig-mcp-scan - MCP Server Security Scanning Tool
  Powered by Tencent Zhuque Lab
  https://github.com/Tencent/AI-Infra-Guard
============================================================
"""


def resolve_runtime_override(args) -> tuple:
    """Resolve LLM override configuration from CLI args or environment variables.

    Returns:
        A (api_key, model, base_url) tuple.
    """
    api_key = (
        args.api_key
        or os.getenv("LLM_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
        or os.getenv("OPENROUTER_API_KEY", "").strip()
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments. Pass argv for programmatic/test invocation."""
    parser = argparse.ArgumentParser(
        prog="aig-mcp-scan",
        description=_BANNER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required arguments
    parser.add_argument("--repo", default="", help="Path to the MCP project directory to scan")

    # Optional arguments
    parser.add_argument("-p", "--prompt", default="", help="Custom scan prompt (optional)")

    parser.add_argument(
        "-m",
        "--model",
        default=config.DEFAULT_MODEL,
        help=f"LLM model name (default: {config.DEFAULT_MODEL})",
    )

    parser.add_argument(
        "-k",
        "--api_key",
        default=None,
        help="API key (falls back to environment variables if omitted)",
    )

    parser.add_argument(
        "-u",
        "--base_url",
        default=config.DEFAULT_BASE_URL,
        help=f"API base URL (default: {config.DEFAULT_BASE_URL})",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
        default=False,
    )

    parser.add_argument("--server_url", help="Remote MCP server URL (for dynamic scanning)", default=None)

    parser.add_argument(
        "--header",
        action="append",
        dest="headers",
        help="Custom header in key:value format (can be used multiple times)",
        default=[],
    )

    parser.add_argument(
        "--language",
        default="zh",
        choices=["zh", "en"],
        help="Output language: zh (Chinese, default) or en (English)",
    )

    parser.add_argument(
        "--aig-mode",
        action="store_true",
        default=False,
        help="Enable AIG integration mode: emit structured JSON logs to stdout "
        "for the Go backend to parse. Not needed for standalone pip install use "
        "(disabled by default).",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=None,
        metavar="FILE",
        help="Save the scan result as a JSON file (optional, e.g. -o result.json)",
    )

    return parser.parse_args(argv)


async def main() -> None:
    """Async main entry point."""
    args = parse_args()

    # AIG integration mode: enabled via --aig-mode when invoked by the Go backend.
    if args.aig_mode:
        mcpLogger.enable()

    override_api_key, override_model, override_base_url = (
        resolve_runtime_override(args)
    )

    api_key = override_api_key
    if not api_key:
        logger.error(
            "API Key not provided. Use --api_key or set LLM_API_KEY/OPENAI_API_KEY/OPENROUTER_API_KEY environment variable."
        )
        sys.exit(1)

    model = override_model or config.DEFAULT_MODEL
    base_url = override_base_url or config.DEFAULT_BASE_URL

    # Create the main LLM instance
    llm = LLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        context_window=config.DEFAULT_MODEL_CONTEXT_WINDOW,
    )
    logger.info(f"Main LLM initialized: {model}")

    # Use main API key as default for specialized LLMs
    llm_manager = LLMManager(api_key=api_key, base_url=base_url)
    specialized_llms = llm_manager.get_specialized_llms(["thinking", "coding"])
    logger.info(f"Specialized LLMs configured: {list(specialized_llms.keys())}")

    user_prompt = args.prompt.strip()
    lang_prompt = _prompts.get(args.language, "")
    prompt = f"{user_prompt}\n\n{lang_prompt}" if user_prompt else lang_prompt
    if prompt:
        logger.info(f"Custom prompt: {prompt}")

    # Parse headers
    headers = {}
    if args.headers:
        for header_item in args.headers:
            try:
                if ":" in header_item:
                    key, value = header_item.split(":", 1)
                    headers[key.strip()] = value.strip()
                elif "=" in header_item:
                    key, value = header_item.split("=", 1)
                    headers[key.strip()] = value.strip()
                else:
                    logger.warning(f"Ignored invalid header format: {header_item}")
            except Exception as e:
                logger.warning(f"Failed to parse header {header_item}: {e}")

        if headers:
            logger.info(f"Custom headers: {headers}")

    if not args.aig_mode:
        print(_BANNER)

    agent = Agent(
        llm=llm,
        specialized_llms=specialized_llms,
        debug=args.debug,
        server_url=args.server_url,
        language=args.language,
        headers=headers,
        aig_mode=args.aig_mode,
    )
    try:
        if args.server_url:
            logger.info(f"Server mode enabled with URL: {args.server_url}")
            result = await agent.dynamic_analysis(prompt)
        else:
            # Validate the project path
            if not os.path.exists(args.repo):
                logger.error(f"Project path does not exist: {args.repo}")
                sys.exit(1)

            if not os.path.isdir(args.repo):
                logger.error(f"Project path is not a directory: {args.repo}")
                sys.exit(1)

            logger.info(f"Starting scan on: {args.repo}")
            result = await agent.scan(args.repo, prompt, args.language)

        logger.info(f"Scan completed successfully:\n\n {result}")

        # Non-AIG mode (standalone CLI usage): output is a SARIF 2.1.0 JSON
        # document so results can be natively consumed by GitHub Code Scanning,
        # Azure DevOps, GitLab Security Dashboard, VS Code Problems panel, etc.
        # AIG mode keeps the original internal dict, since the Go backend
        # consumes it via mcpLogger, not this file.
        output_data = result
        if not args.aig_mode and not args.server_url:
            output_data = to_sarif(
                result, tool_version=_AIG_MCP_SCAN_VERSION, language=args.language
            )

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
                logger.info(f"Result saved to: {args.output}")
            except OSError as e:
                logger.error(f"Failed to write output file {args.output}: {e}")
        elif not args.aig_mode:
            # CLI standalone mode without -o: print SARIF JSON to stdout
            print(json.dumps(output_data, ensure_ascii=False, indent=2, default=str))
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


def cli() -> None:
    """Sync entry point used by console_scripts (the ``aig-mcp-scan`` command) and ``python -m mcp_scan``."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
