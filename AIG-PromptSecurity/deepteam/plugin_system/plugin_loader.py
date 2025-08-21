from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import json
from loguru import logger

from .plugin_validator import PluginValidator
from .plugin_registry import PluginRegistry


class PluginLoader:
    """插件加载器，负责扫描和加载插件"""
    
    def __init__(self, registry: Optional[PluginRegistry] = None):
        self.validator = PluginValidator()
        self.registry = registry or PluginRegistry()
        self.default_plugin_dirs = [
            Path("./plugin"),
            Path("./custom_plugins"),
            Path.home() / ".deepteam" / "plugins"
        ]
    
    def load_plugin(self, plugin_path: Union[str, Path]) -> Dict[str, Any]:
        """加载单个插件"""
        plugin_path = Path(plugin_path)
        
        result = {
            'success': False,
            'plugin_info': None,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 验证插件
            if plugin_path.is_file():
                validation_result = self.validator.validate_plugin_file(plugin_path)
            elif plugin_path.is_dir():
                validation_result = self.validator.validate_plugin_directory(plugin_path)
            else:
                result['errors'].append(f"路径不存在: {plugin_path}")
                return result
            
            # 处理验证结果
            if validation_result['valid']:
                if plugin_path.is_file():
                    # 单个文件
                    if self.registry.register_plugin(plugin_path, validation_result):
                        result['success'] = True
                        result['plugin_info'] = validation_result
                    else:
                        result['errors'].append("插件注册失败")
                else:
                    # 目录
                    success_count = 0
                    for plugin_info in validation_result['plugins']:
                        # 为每个插件找到对应的文件
                        plugin_file = self._find_plugin_file(plugin_path, plugin_info['class_name'])
                        if plugin_file and self.registry.register_plugin(plugin_file, plugin_info):
                            success_count += 1
                    
                    if success_count > 0:
                        result['success'] = True
                        result['plugin_info'] = {
                            'type': 'directory',
                            'loaded_count': success_count,
                            'total_count': len(validation_result['plugins'])
                        }
                    else:
                        result['errors'].append("没有成功加载任何插件")
            else:
                result['errors'].extend(validation_result['errors'])
                result['warnings'].extend(validation_result['warnings'])
                
        except Exception as e:
            result['errors'].append(f"加载插件时发生错误: {str(e)}")
        
        return result
    
    def _find_plugin_file(self, dir_path: Path, class_name: str) -> Optional[Path]:
        """在目录中查找包含指定类的文件"""
        for py_file in dir_path.glob("*.py"):
            try:
                validation_result = self.validator.validate_plugin_file(py_file)
                if validation_result['valid'] and validation_result['class_name'] == class_name:
                    return py_file
            except Exception:
                continue
        return None
    
    def load_plugins_from_directory(self, dir_path: Union[str, Path]) -> Dict[str, Any]:
        """从目录加载所有插件"""
        dir_path = Path(dir_path)
        
        result = {
            'success': False,
            'loaded_plugins': [],
            'errors': [],
            'warnings': []
        }
        
        try:
            if not dir_path.exists() or not dir_path.is_dir():
                result['errors'].append(f"目录不存在或不是有效目录: {dir_path}")
                return result
            
            # 验证目录
            validation_result = self.validator.validate_plugin_directory(dir_path)
            
            if validation_result['valid']:
                success_count = 0
                for plugin_info in validation_result['plugins']:
                    plugin_file = self._find_plugin_file(dir_path, plugin_info['class_name'])
                    if plugin_file and self.registry.register_plugin(plugin_file, plugin_info):
                        success_count += 1
                        result['loaded_plugins'].append({
                            'file': str(plugin_file),
                            'class': plugin_info['class_name'],
                            'type': plugin_info['plugin_type']
                        })
                
                if success_count > 0:
                    result['success'] = True
                    logger.info(f"从目录 {dir_path} 成功加载了 {success_count} 个插件")
                else:
                    result['errors'].append("没有成功加载任何插件")
            else:
                result['errors'].extend(validation_result['errors'])
                result['warnings'].extend(validation_result['warnings'])
                
        except Exception as e:
            result['errors'].append(f"加载插件目录时发生错误: {str(e)}")
        
        return result
    
    def auto_discover_plugins(self) -> Dict[str, Any]:
        """自动发现并加载插件"""
        result = {
            'success': False,
            'discovered_dirs': [],
            'loaded_plugins': [],
            'errors': [],
            'warnings': []
        }
        
        for plugin_dir in self.default_plugin_dirs:
            if plugin_dir.exists() and plugin_dir.is_dir():
                result['discovered_dirs'].append(str(plugin_dir))
                dir_result = self.load_plugins_from_directory(plugin_dir)
                
                if dir_result['success']:
                    result['loaded_plugins'].extend(dir_result['loaded_plugins'])
                else:
                    result['errors'].extend(dir_result['errors'])
                    result['warnings'].extend(dir_result['warnings'])
        
        result['success'] = len(result['loaded_plugins']) > 0
        
        if result['success']:
            logger.info(f"自动发现并加载了 {len(result['loaded_plugins'])} 个插件")
        
        return result
    
    def load_plugins_from_config(self, config_file: Union[str, Path]) -> Dict[str, Any]:
        """从配置文件加载插件"""
        config_file = Path(config_file)
        
        result = {
            'success': False,
            'loaded_plugins': [],
            'errors': [],
            'warnings': []
        }
        
        try:
            if not config_file.exists():
                result['errors'].append(f"配置文件不存在: {config_file}")
                return result
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 处理插件配置
            plugins_config = config.get('plugins', [])
            
            for plugin_config in plugins_config:
                plugin_path = plugin_config.get('path')
                if not plugin_path:
                    result['errors'].append("插件配置缺少path字段")
                    continue
                
                plugin_result = self.load_plugin(plugin_path)
                if plugin_result['success']:
                    result['loaded_plugins'].append({
                        'path': plugin_path,
                        'info': plugin_result['plugin_info']
                    })
                else:
                    result['errors'].extend(plugin_result['errors'])
                    result['warnings'].extend(plugin_result['warnings'])
            
            result['success'] = len(result['loaded_plugins']) > 0
            
        except json.JSONDecodeError as e:
            result['errors'].append(f"配置文件格式错误: {e}")
        except Exception as e:
            result['errors'].append(f"加载配置文件时发生错误: {str(e)}")
        
        return result
    
    def get_loaded_plugins(self) -> Dict[str, List[str]]:
        """获取已加载的插件列表"""
        return self.registry.list_plugins()
    
    def get_plugin_info(self, plugin_key: str) -> Optional[Dict[str, Any]]:
        """获取插件详细信息"""
        return self.registry.get_plugin_info(plugin_key)
    
    def unload_plugin(self, plugin_key: str) -> bool:
        """卸载插件"""
        return self.registry.unregister_plugin(plugin_key)
    
    def reload_plugin(self, plugin_path: Union[str, Path]) -> Dict[str, Any]:
        """重新加载插件"""
        plugin_path = Path(plugin_path)
        
        # 先卸载已存在的插件
        plugin_info = self.registry.get_plugin_info(f"attack_{plugin_path.stem}")
        if not plugin_info:
            plugin_info = self.registry.get_plugin_info(f"metric_{plugin_path.stem}")
        
        if plugin_info:
            self.registry.unregister_plugin(f"{plugin_info['type']}_{plugin_info['class_name']}")
        
        # 重新加载
        return self.load_plugin(plugin_path) 