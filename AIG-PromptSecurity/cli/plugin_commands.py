from typing import List
from deepteam.plugin_system import PluginManager
from .mappings import TECHNIQUE_CLASS_MAP, SCENARIO_CLASS_MAP, METRIC_CLASS_MAP


def load_plugins_from_args(plugin_paths: List[str], plugin_manager: PluginManager) -> None:
    """从命令行参数加载插件"""
    if not plugin_paths:
        return
    
    print("正在加载自定义插件...")
    for plugin_path in plugin_paths:
        result = plugin_manager.load_plugin(plugin_path)
        if result['success']:
            print(f"✓ 成功加载插件: {plugin_path}")
            if result['warnings']:
                for warning in result['warnings']:
                    print(f"  警告: {warning}")
        else:
            print(f"✗ 加载插件失败: {plugin_path}")
            for error in result['errors']:
                print(f"  错误: {error}")


def list_plugins(plugin_manager: PluginManager) -> None:
    """列出所有可用插件"""
    print("\n=== 内置攻击插件 ===")
    for name in TECHNIQUE_CLASS_MAP.keys():
        print(f"  {name}")
    
    print("\n=== 内置漏洞场景 ===")
    for name in SCENARIO_CLASS_MAP.keys():
        print(f"  {name}")
    
    print("\n=== 内置指标 ===")
    for name in METRIC_CLASS_MAP.keys():
        print(f"  {name}")
    
    # 显示自定义插件
    custom_plugins = plugin_manager.get_loaded_plugins()
    if custom_plugins['attacks']:
        print("\n=== 自定义攻击插件 ===")
        for name in custom_plugins['attacks']:
            print(f"  {name}")
    
    if custom_plugins['vulnerabilities']:
        print("\n=== 自定义漏洞插件 ===")
        for name in custom_plugins['vulnerabilities']:
            print(f"  {name}")
    
    if custom_plugins['metrics']:
        print("\n=== 自定义指标插件 ===")
        for name in custom_plugins['metrics']:
            print(f"  {name}")


def show_plugin_template(plugin_type: str, plugin_manager: PluginManager) -> None:
    """显示插件模板"""
    template = plugin_manager.get_plugin_template(plugin_type)
    print(f"\n=== {plugin_type.title()} 插件模板 ===")
    print(template)


def validate_plugin(plugin_path: str, plugin_manager: PluginManager) -> None:
    """验证插件"""
    result = plugin_manager.validate_plugin(plugin_path)
    if result['valid']:
        print(f"✓ 插件验证通过: {plugin_path}")
        print(f"  类型: {result['plugin_type']}")
        print(f"  类名: {result['class_name']}")
        if result['warnings']:
            for warning in result['warnings']:
                print(f"  警告: {warning}")
    else:
        print(f"✗ 插件验证失败: {plugin_path}")
        for error in result['errors']:
            print(f"  错误: {error}")


def auto_discover_plugins(plugin_manager: PluginManager) -> None:
    """自动发现插件"""
    print("自动发现插件...")
    result = plugin_manager.auto_discover_plugins()
    if result['success']:
        print(f"✓ 自动发现并加载了 {len(result['loaded_plugins'])} 个插件")
        for plugin in result['loaded_plugins']:
            print(f"  - {plugin['class']} ({plugin['type']})")
    else:
        print("没有发现任何插件") 