import sys
import argparse

from cli.aig_logger import logger
from cli.aig_logger import (
    newPlanStep, statusUpdate, toolUsed, actionLog, resultUpdate
)
from deepteam.plugin_system import PluginManager
from cli.models import create_model
from cli.plugin_commands import list_plugins, load_plugins_from_args, show_plugin_template, validate_plugin, auto_discover_plugins
from cli.red_team_runner import RedTeamRunner
from cli.tool_scanner_cli import handle_tool_scanning


# logger config
logger.add("logs/red_team.log", rotation="00:00", level="DEBUG", enqueue=True, retention="7 days")

# 全局插件管理器
plugin_manager = PluginManager()


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

    # 初始化模型
    models = []
    lengths = list(map(len, (args.base_url, args.api_key, args.model, args.max_concurrent)))
    if len(set(lengths)) != 1:
        raise ValueError("base_url, api_key, model, max_concurrent must have same number of parameters")
    for base_url, api_key, model_name, max_concurrent  in zip(args.base_url, args.api_key, args.model, args.max_concurrent):
        model = create_model(model_name, base_url, api_key[0], max_concurrent)
        models.append(model)
        
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


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(e)
        logger.critical_issue(content=logger.translated_msg("Something went wrong. Please try again in a few moments."))
