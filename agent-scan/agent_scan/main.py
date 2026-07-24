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

"""aig-agent-scan CLI entry point.

Can be run either as a module (``python -m agent_scan``) or as a console
script (``aig-agent-scan``); also exposes the :func:`main` async entry point
for programmatic use.

Two modes:
  - CLI mode (default): runs the full three-stage pipeline and outputs a
    structured JSON report to stdout or a file.
  - AIG mode (``--aig-mode``): emits structured JSON logs to stdout for the
    Go backend to parse and display in the AIG Web UI.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from agent_scan import __version__ as _AIG_AGENT_SCAN_VERSION
from agent_scan.core.agent import Agent
from agent_scan.core.agent_adapter.adapter import AIProviderClient
from agent_scan.core.agent_adapter.connectivity import connectivity
from agent_scan.utils import config
from agent_scan.utils.aig_logger import scanLogger
from agent_scan.utils.llm import LLM
from agent_scan.utils.llm_manager import LLMManager
from agent_scan.utils.logging import logger

# Important: import the tools package to trigger tool registration
import agent_scan.tools as _  # isort: skip

_prompts = {"zh": "所有回复都应使用中文。", "en": "All responses should be in English."}

_BANNER = """\
============================================================
  aig-agent-scan - AI Agent Security Scanning Tool
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
        prog="aig-agent-scan",
        description=_BANNER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required arguments
    parser.add_argument("--repo", default="", help="Path to the project directory to scan (optional, for source audit)")

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
        "--agent_provider",
        default="",
        help="Agent provider YAML file (required for dynamic testing)",
    )

    parser.add_argument(
        "--language",
        default="zh",
        choices=["zh", "en"],
        help="Output language: zh (Chinese, default) or en (English)",
    )

    parser.add_argument(
        "--skills",
        default=None,
        help="Comma-separated detection skill names to run "
        "(e.g. 'web-exfiltration-detection'). If not specified, all default "
        "detection skills will be used.",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
        default=False,
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
        scanLogger.enable()

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
    llm = LLM(model=model, api_key=api_key, base_url=base_url)
    logger.info(f"Main LLM initialized: {model}")

    # Use main API key as default for specialized LLMs
    llm_manager = LLMManager(api_key=api_key, base_url=base_url)
    specialized_llms = llm_manager.get_specialized_llms(["thinking", "coding"])
    logger.info(f"Specialized LLMs configured: {list(specialized_llms.keys())}")

    # Load agent provider
    agent_provider = args.agent_provider
    if agent_provider:
        default_client = AIProviderClient()
        if not connectivity(default_client, agent_provider):
            logger.error("Agent provider is not valid")
            scanLogger.error_log("Agent provider is not valid")
            return

    user_prompt = args.prompt.strip()
    lang_prompt = _prompts.get(args.language, "")
    prompt = f"{user_prompt}\n\n{lang_prompt}" if user_prompt else lang_prompt
    if prompt:
        logger.info(f"Custom prompt: {prompt}")

    if not args.aig_mode:
        print(_BANNER)

    agent = Agent(
        llm=llm,
        specialized_llms=specialized_llms,
        debug=args.debug,
        language=args.language,
        agent_provider=agent_provider,
        skills=args.skills.split(",") if args.skills else None,
    )
    try:
        logger.info(f"Starting scan on: {args.repo}")
        result = await agent.scan(args.repo, prompt)

        logger.info(f"Scan completed successfully:\n\n {result}")

        # Non-AIG mode (standalone CLI usage): output is a JSON report.
        # AIG mode keeps the original internal dict, since the Go backend
        # consumes it via scanLogger, not this file.
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                logger.info(f"Result saved to: {args.output}")
            except OSError as e:
                logger.error(f"Failed to write output file {args.output}: {e}")
        elif not args.aig_mode:
            # CLI standalone mode without -o: print JSON report to stdout
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    except KeyboardInterrupt:
        print("\n\nTask interrupted by user.")
        logger.warning("Task interrupted by user")
    except Exception as e:
        print(f"\n\nError during execution: {e}")
        logger.error(f"Error during execution: {e}")
        import traceback

        tb = traceback.format_exc()
        scanLogger.error_log(f"Execution failed: {e}\n{tb}")
        raise
    finally:
        # Clean up any dispatcher resources
        if hasattr(agent, "dispatcher"):
            try:
                await agent.dispatcher.close()
            except Exception:
                pass


def cli() -> None:
    """Sync entry point used by console_scripts (the ``aig-agent-scan`` command) and ``python -m agent_scan``."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
