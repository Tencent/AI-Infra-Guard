import sys
import argparse
from cli.aig_logger import logger
from cli.aig_logger import (
    newPlanStep, statusUpdate, toolUsed, actionLog, resultUpdate
)
from deepteam.plugin_system import PluginManager
from cli import (
    create_model,
    load_plugins_from_args,
    list_plugins,
    show_plugin_template,
    validate_plugin,
    auto_discover_plugins,
    RedTeamRunner,
    handle_tool_scanning
)

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
    parser.add_argument("--base_url", type=str, help="Base URL for ChatOpenAI")
    parser.add_argument("--model", type=str, help="Model name for ChatOpenAI")
    parser.add_argument("--simulator_model", type=str, default=None, help="Simulator model name for ChatOpenAI")
    parser.add_argument("--evaulate_model", type=str, default=None, help="Evaulate model name for ChatOpenAI")
    parser.add_argument("--api_key", type=str, help="API Key for ChatOpenAI")
    parser.add_argument("--scenarios", type=str, nargs='+', help="Scenarios to test")
    parser.add_argument("--techniques", type=str, nargs='+', help="Techniques to test")
    parser.add_argument("--async_mode", action='store_true', help="Enable async mode")
    parser.add_argument("--choice", type=str, default="random", choices=["random", "serial", "parallel"], 
                       help="Technique selection strategy: 'random' (default) or 'serial' (nested techniques) or 'parallel'")
    parser.add_argument("--metric", type=str, help="Metric class name (e.g., 'RandomMetric')")
    parser.add_argument("--report", type=str, default="logs/report.md", help="Path to save the risk assessment report (default: logs/report.md)")
    
    args = parser.parse_args()

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

    # 检查红队测试必需参数
    if not all([args.model, args.base_url, args.api_key, args.scenarios, args.techniques]):
        parser.error("红队测试需要以下必需参数: --model, --base_url, --api_key, --scenarios, --techniques")

    # 初始化模型
    model = create_model(args.model, args.base_url, args.api_key)
    if args.simulator_model is None:
        simulator_model = model
    else:
        simulator_model = create_model(args.simulator_model, args.base_url, args.api_key)
    if args.evaulate_model is None:
        evaulate_model = model
    else:
        evaulate_model = create_model(args.evaulate_model, args.base_url, args.api_key)
    # 创建红队运行器
    runner = RedTeamRunner(plugin_manager)
    
    # 运行红队测试
    report_path = runner.run_red_team(
        model=model,
        simulator_model=simulator_model,
        evaulate_model=evaulate_model,
        scenarios=args.scenarios,
        techniques=args.techniques,
        async_mode=args.async_mode,
        choice=args.choice,
        metric=args.metric,
        report_path=args.report
    )
    
    logger.info(f'Original report save to: {report_path}')


if __name__ == "__main__":
    main()
