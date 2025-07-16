"""
工具扫描CLI模块
处理工具扫描相关的命令行功能
"""

from deepteam.plugin_system.tool_scanner import ToolScanner


def handle_tool_scanning(args):
    """处理工具扫描相关命令"""
    scanner = ToolScanner()
    
    # 添加插件路径
    if args.plugins:
        for plugin_path in args.plugins:
            scanner.add_plugin_path(plugin_path)
    
    # 扫描所有工具
    tools_info = scanner.scan_all_tools()
    
    if args.scan_tools:
        print("=== 可用工具列表 ===")
        
        # 根据参数选择要显示的工具类型
        tool_types = []
        if args.scan_tools == "all":
            tool_types = ['attack', 'metric', 'vulnerability']
        elif args.scan_tools == "techniques":
            tool_types = ['attack']
        elif args.scan_tools == "metrics":
            tool_types = ['metric']
        elif args.scan_tools == "scenarios":
            tool_types = ['vulnerability']
        
        for tool_type in tool_types:
            # 显示用户友好的类型名称
            display_name = {
                'attack': 'TECHNIQUES (攻击技术)',
                'metric': 'METRICS (评估指标)',
                'vulnerability': 'SCENARIOS (测试场景)'
            }.get(tool_type, tool_type.upper())
            
            print(f"\n## {display_name}:")
            tools_of_type = scanner.get_tools_by_type(tool_type)
            if tools_of_type:
                for tool_name, tool_info in tools_of_type.items():
                    print(f"  - {tool_name}")
                    if tool_info['parameters']:
                        for param_name, param_info in tool_info['parameters'].items():
                            required = "必需" if param_info['required'] else "可选"
                            default_str = f" (默认: {param_info['default']})" if param_info['default'] is not None else ""
                            print(f"    * {param_name} ({required}){default_str}")
                            if param_info['description']:
                                print(f"      {param_info['description']}")
            else:
                print("  (无可用工具)")
        
        # 显示验证警告
        warnings = scanner.validate_tool_completeness()
        if warnings:
            print("\n=== 验证警告 ===")
            for warning in warnings:
                print(warning)
        
        return True
    
    if args.show_tool_params:
        tool_name = args.show_tool_params
        tool_info = scanner.get_tool_info(tool_name)
        
        if tool_info:
            print(f"=== {tool_name} 详细信息 ===")
            print(f"类型: {tool_info['type']}")
            print(f"文件: {tool_info['file']}")
            if tool_info['description']:
                print(f"描述: {tool_info['description']}")
            
            if tool_info['parameters']:
                print("\n参数:")
                for param_name, param_info in tool_info['parameters'].items():
                    required = "必需" if param_info['required'] else "可选"
                    default_str = f" (默认值: {param_info['default']})" if param_info['default'] is not None else ""
                    print(f"  {param_name} ({required}){default_str}")
                    if param_info['description']:
                        print(f"    描述: {param_info['description']}")
            else:
                print("\n参数: (无参数)")
        else:
            print(f"错误: 找不到工具 '{tool_name}'")
            print("可用工具:")
            for tool_name in tools_info.keys():
                print(f"  - {tool_name}")
        
        return True
    
    return False 