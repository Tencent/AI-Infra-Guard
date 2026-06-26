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

import time
from pathlib import Path
import argparse
import json

from cli.aig_logger import logger
from cli.aig_logger import (
    newPlanStep, statusUpdate, toolUsed, actionLog, resultUpdate
)
from deepteam.plugin_system import PluginManager
from cli.models import create_model
from cli.plugin_commands import list_plugins, load_plugins_from_args, show_plugin_template, validate_plugin, auto_discover_plugins
from cli.red_team_runner import RedTeamRunner
from cli.reasoning_backdoor_badchain_models import BadChainPromptedModel
from cli.reasoning_backdoor_models import DatasetOracleModel, PoisonedModelWrapper
from cli.reasoning_backdoor_runner import ReasoningBackdoorRunner
from cli.tool_scanner_cli import handle_tool_scanning


# logger config
logger.add(f"logs/red_team_{{time:YYYY-MM-DD_HH-mm-ss}}.log", level="DEBUG", enqueue=True, retention="7 days")

# 全局插件管理器
plugin_manager = PluginManager()

def cleanup_expired_files(log_path: str = "logs", max_age_seconds: int = 86400*30, pattern: str = "attachment_*.csv"):
    now = time.time()
    for file in Path(log_path).glob(pattern):
        if (now - file.stat().st_mtime) > max_age_seconds:
            file.unlink()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Red Team CLI Runner")
    
    # 工具扫描相关参数（放在最前面，优先级最高）
    parser.add_argument("--scan-tools", type=str, choices=["all", "techniques", "metrics", "scenarios"], 
                       help="Scan and display all available tools and their parameters")
    parser.add_argument("--show-tool-params", type=str, 
                       help="Show detailed parameter information for a specific tool")
    
    # 插件相关参数
    parser.add_argument("--plugins", type=str, nargs='+', help="Custom plugin files or directories to load")
    parser.add_argument("--list-plugins", action="store_true", help="List all available plugins")
    parser.add_argument("--show-template", type=str, choices=["attack", "metric", "vulnerability"], help="Show plugin template")
    parser.add_argument("--validate-plugin", type=str, help="Validate a plugin file or directory")
    parser.add_argument("--auto-discover", action="store_true", help="Auto-discover plugins from default directories")
    
    # 红队测试相关参数
    parser.add_argument("--base_url", type=str, action='append', help="Base URL for ChatOpenAI")
    parser.add_argument("--api_key", type=str, nargs=1, action='append', help="API Key for ChatOpenAI")
    parser.add_argument("--model", type=str, action='append', help="Model name for ChatOpenAI")
    parser.add_argument("--max_concurrent", type=int, action='append', help="Max concurrent")
    parser.add_argument("--sim_base_url", type=str, help="Base URL for a simulator model")
    parser.add_argument("--sim_api_key", type=str, nargs=1, help="API Key for a simulator model")
    parser.add_argument("--simulator_model", type=str, help="Model name for a simulator model")
    parser.add_argument("--sim_max_concurrent", type=int, default=10, help="Max concurrent")
    parser.add_argument("--eval_base_url", type=str, help="Base URL for a evaluate model")
    parser.add_argument("--eval_api_key", type=str, nargs=1, help="API Key for a evaluate model")
    parser.add_argument("--evaluate_model", type=str, help="Model name for a evaluate model")
    parser.add_argument("--eval_max_concurrent", type=int, default=10, help="Max concurrent")

    parser.add_argument("--scenarios", type=str, nargs='+', help="Scenarios to test")
    parser.add_argument("--techniques", type=str, nargs='+', help="Techniques to test")
    
    parser.add_argument("--async_mode", action='store_true', help="Enable async mode")
    parser.add_argument("--choice", type=str, default="random", choices=["random", "serial", "parallel"], 
                       help="Technique selection strategy: 'random' (default) or 'serial' (nested techniques) or 'parallel'")
    parser.add_argument("--metric", type=str, help="Metric class name (e.g., 'RandomMetric')")
    parser.add_argument("--report", type=str, default="logs/report.md", help="Path to save the risk assessment report (default: logs/report.md)")
    parser.add_argument("--lang", type=str, default="zh_CN", help="Report language")
    parser.add_argument("--reasoning-backdoor-dataset", type=str, help="Run paired reasoning backdoor evaluation with the given JSONL dataset")
    parser.add_argument("--reasoning-trigger-family", type=str, default="cot_tba", help="Trigger family for paired reasoning backdoor evaluation")
    parser.add_argument("--reasoning-output", type=str, default="logs/reasoning_backdoor_report.json", help="Path to save reasoning backdoor evaluation JSON report")
    parser.add_argument("--reasoning-limit", type=int, help="Limit the number of reasoning backdoor samples to run")
    parser.add_argument("--reasoning-progress", action="store_true", help="Print per-sample progress for reasoning backdoor evaluation")
    parser.add_argument("--reasoning-oracle-clean", action="store_true", help="Use deterministic clean oracle for reasoning backdoor negative-control testing")
    parser.add_argument("--reasoning-poison-mode", type=str, choices=sorted(PoisonedModelWrapper.SUPPORTED_MODES), help="Wrap oracle model with simulated poisoned behavior")
    parser.add_argument("--reasoning-badchain-root", type=str, help="Path to BadChain repo for real in-context backdoor validation")
    parser.add_argument("--reasoning-badchain-task", type=str, default="ASDiv", help="BadChain task name, such as ASDiv or gsm8k")
    parser.add_argument("--reasoning-badchain-clean-cot", type=str, default="8_clean", help="BadChain clean CoT prompt id")
    parser.add_argument("--reasoning-badchain-poisoned-cot", type=str, default="8_s01_4+4", help="BadChain poisoned CoT prompt id")
    parser.add_argument("--reasoning-badchain-mode", type=str, choices=sorted(BadChainPromptedModel.MODES), default="auto", help="BadChain prompt setup mode")
    parser.add_argument("--reasoning-max-output-tokens", type=int, help="Override max completion tokens for reasoning backdoor model calls")
    parser.add_argument("--reasoning-self-consistency-samples", type=int, default=1, help="Optional repeated clean/trigger samples per reasoning case for self-consistency signals")
    
    args = parser.parse_args()

    logger.set_language(lang=args.lang)

    # 处理工具扫描相关命令（优先级最高）
    if args.scan_tools or args.show_tool_params:
        if handle_tool_scanning(args):
            exit(0)

    # 处理插件相关命令
    if args.show_template:
        show_plugin_template(args.show_template, plugin_manager)
        exit(0)
    
    if args.validate_plugin:
        validate_plugin(args.validate_plugin, plugin_manager)
        exit(0)
    
    # 加载插件（在list_plugins之前）
    if args.auto_discover:
        auto_discover_plugins(plugin_manager)
    
    if args.plugins:
        load_plugins_from_args(args.plugins, plugin_manager)
    
    if args.list_plugins:
        list_plugins(plugin_manager)
        exit(0)

    if args.reasoning_backdoor_dataset:
        if args.reasoning_oracle_clean and args.reasoning_poison_mode:
            raise ValueError("--reasoning-oracle-clean and --reasoning-poison-mode are mutually exclusive")
        if args.reasoning_oracle_clean:
            target_model = DatasetOracleModel(
                dataset_file=args.reasoning_backdoor_dataset,
                model_name="reasoning-oracle-clean",
            )
        elif args.reasoning_poison_mode:
            clean_model = DatasetOracleModel(dataset_file=args.reasoning_backdoor_dataset)
            target_model = PoisonedModelWrapper(
                base_model=clean_model,
                dataset_file=args.reasoning_backdoor_dataset,
                mode=args.reasoning_poison_mode,
                model_name="reasoning-poisoned-control",
            )
        else:
            models = _create_target_models(args)
            if len(models) != 1:
                raise ValueError("reasoning backdoor evaluation currently supports exactly one target model")
            target_model = models[0]
            if args.reasoning_badchain_root:
                target_model = BadChainPromptedModel(
                    base_model=target_model,
                    badchain_root=args.reasoning_badchain_root,
                    task=args.reasoning_badchain_task,
                    clean_cot=args.reasoning_badchain_clean_cot,
                    poisoned_cot=args.reasoning_badchain_poisoned_cot,
                    mode=args.reasoning_badchain_mode,
                    max_output_tokens=args.reasoning_max_output_tokens,
                )
            is_connection, msg = target_model.test_model_connection()
            if not is_connection:
                raise ValueError(f"Load model {target_model.get_model_name()} failed: {msg}")
        runner = ReasoningBackdoorRunner(
            model=target_model,
            dataset_file=args.reasoning_backdoor_dataset,
            trigger_family=args.reasoning_trigger_family,
            output_path=args.reasoning_output,
            sample_limit=args.reasoning_limit,
            show_progress=args.reasoning_progress,
            self_consistency_samples=args.reasoning_self_consistency_samples,
        )
        report = runner.run()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    # 初始化模型
    models = _create_target_models(args)
        
    if any(param is None for param in (args.evaluate_model, args.eval_base_url, args.eval_api_key, args.eval_max_concurrent)):
        evaluate_model = models[0]
    else:
        evaluate_model = create_model(args.evaluate_model, args.eval_base_url, args.eval_api_key[0], args.eval_max_concurrent)

    if any(param is None for param in (args.simulator_model, args.sim_base_url, args.sim_api_key, args.sim_max_concurrent)):
        simulator_model = evaluate_model
    else:
        simulator_model = create_model(args.simulator_model, args.sim_base_url, args.sim_api_key[0], args.sim_max_concurrent)

    # 创建红队运行器
    runner = RedTeamRunner(plugin_manager)
    
    # 运行红队测试
    runner.run_red_team(
        models=models,
        simulator_model=simulator_model,
        evaluate_model=evaluate_model,
        scenarios=args.scenarios,
        techniques=args.techniques,
        async_mode=args.async_mode,
        choice=args.choice,
        metric=args.metric,
        report_path=args.report,
    )


def _create_target_models(args):
    required_args = (args.base_url, args.api_key, args.model, args.max_concurrent)
    if any(arg is None for arg in required_args):
        raise ValueError("base_url, api_key, model, max_concurrent are required")

    models = []
    lengths = list(map(len, required_args))
    if len(set(lengths)) != 1:
        raise ValueError("base_url, api_key, model, max_concurrent must have same number of parameters")
    for base_url, api_key, model_name, max_concurrent in zip(args.base_url, args.api_key, args.model, args.max_concurrent):
        model = create_model(model_name, base_url, api_key[0], max_concurrent)
        models.append(model)
    return models


if __name__ == "__main__":
    try:
        main()
        # 清理过期文件
        cleanup_expired_files()
    except Exception as e:
        logger.error(e)
        logger.critical_issue(content=logger.translated_msg("Something went wrong. Please try again in a few moments."))
