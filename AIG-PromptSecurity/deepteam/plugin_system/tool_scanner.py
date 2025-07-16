"""
工具扫描器模块
用于扫描所有可用的工具并提取参数信息，支持CLI展示
"""

import os
import glob
import importlib
import inspect
from typing import Dict, List, Optional, Any
from pathlib import Path


class ToolScanner:
    """工具扫描器，用于扫描和提取工具信息"""
    
    def __init__(self):
        self.tools_info = {}
        self.plugin_paths = []
        self.remote_plugin_urls = []
    
    def add_plugin_path(self, path: str):
        """添加插件路径"""
        if os.path.exists(path):
            self.plugin_paths.append(path)
    
    def add_remote_plugin_url(self, url: str):
        """添加远程插件URL"""
        if url.startswith('http') and (url.endswith('.zip') or url.endswith('.py')):
            self.remote_plugin_urls.append(url)
    
    def scan_all_tools(self) -> Dict[str, Any]:
        """扫描所有可用的工具"""
        self.tools_info = {}
        
        # 扫描内置工具
        self._scan_builtin_tools()
        # 扫描插件工具
        self._scan_plugin_tools()
        # 扫描远程插件工具
        self._scan_remote_plugin_tools()
        
        return self.tools_info
    
    def _scan_remote_plugin_tools(self):
        """扫描远程插件工具"""
        if not self.remote_plugin_urls:
            return
            
        try:
            from .remote_plugin_downloader import RemotePluginDownloader
            downloader = RemotePluginDownloader()
            
            for url in self.remote_plugin_urls:
                # 下载并解压远程插件
                download_result = downloader.download_and_extract_plugin(url)
                if download_result['success'] and download_result['extracted_path']:
                    # 扫描解压后的插件
                    self._scan_plugin_directory(download_result['extracted_path'])
        except ImportError:
            print("Warning: 远程插件下载器不可用，跳过远程插件扫描")
        except Exception as e:
            print(f"Warning: 扫描远程插件时发生错误: {e}")
    
    def _scan_builtin_tools(self):
        """扫描内置工具"""
        # 扫描 deepteam/attacks/ 目录
        self._scan_directory('deepteam/attacks/', 'attack')
        # 扫描 deepteam/metrics/ 目录  
        self._scan_directory('deepteam/metrics/', 'metric')
        # 扫描 deepteam/vulnerabilities/ 目录
        self._scan_directory('deepteam/vulnerabilities/', 'vulnerability')
    
    def _scan_plugin_tools(self):
        """扫描插件工具"""
        # 扫描 plugin/ 目录下的插件
        if os.path.exists('plugin/'):
            self._scan_plugin_directory('plugin/')
        
        # 扫描用户指定的插件路径
        for plugin_path in self.plugin_paths:
            self._scan_plugin_directory(plugin_path)
    
    def _scan_directory(self, directory: str, tool_type: str):
        """扫描指定目录下的工具"""
        if not os.path.exists(directory):
            return
            
        for file_path in glob.glob(f"{directory}/**/*.py", recursive=True):
            if self._is_tool_file(file_path):
                tool_info = self._extract_tool_info(file_path, tool_type)
                if tool_info:
                    self.tools_info[tool_info['name']] = tool_info
    
    def _scan_plugin_directory(self, plugin_path: str):
        """扫描插件目录"""
        if os.path.isfile(plugin_path):
            # 单个文件插件
            if plugin_path.endswith('.py'):
                tool_infos = self._extract_tool_info_from_file(plugin_path)
                for tool_info in tool_infos:
                    self.tools_info[tool_info['name']] = tool_info
        elif os.path.isdir(plugin_path):
            # 文件夹插件
            for file_path in glob.glob(f"{plugin_path}/**/*.py", recursive=True):
                tool_infos = self._extract_tool_info_from_file(file_path)
                for tool_info in tool_infos:
                    self.tools_info[tool_info['name']] = tool_info
    
    def _is_tool_file(self, file_path: str) -> bool:
        """判断是否为工具文件"""
        # 排除 __init__.py 和测试文件
        filename = os.path.basename(file_path)
        if filename.startswith('__') or filename.startswith('test_'):
            return False
        
        # 检查文件内容是否包含工具类
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 简单检查是否包含工具基类
                tool_keywords = ['BaseAttack', 'BaseRedTeamingMetric', 'BaseVulnerability']
                return any(keyword in content for keyword in tool_keywords)
        except:
            return False
    
    def _extract_tool_info(self, file_path: str, tool_type: str) -> Optional[Dict[str, Any]]:
        """从文件中提取工具信息"""
        try:
            # 转换为模块路径
            module_path = self._file_path_to_module_path(file_path)
            if not module_path:
                return None
            
            # 动态导入模块
            module = importlib.import_module(module_path)
            
            # 查找工具类
            tool_class = self._find_tool_class(module, tool_type)
            if not tool_class:
                return None
            
            # 提取参数信息
            param_info = self._extract_parameters(tool_class)
            
            return {
                'name': tool_class.__name__,
                'type': tool_type,
                'file': file_path,
                'description': getattr(tool_class, '__doc__', ''),
                'parameters': param_info,
                'has_parameter_descriptions': hasattr(tool_class, '_parameter_descriptions')
            }
        except Exception as e:
            print(f"Warning: Failed to scan {file_path}: {e}")
            return None
    
    def _extract_tool_info_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """从插件文件中提取工具信息"""
        try:
            # 转换为模块路径
            module_path = self._file_path_to_module_path(file_path)
            if not module_path:
                return []
            
            # 动态导入模块
            module = importlib.import_module(module_path)
            
            # 查找所有工具类
            all_tools = []
            for tool_type in ['attack', 'metric', 'vulnerability']:
                tool_classes = self._find_all_tool_classes(module, tool_type)
                for tool_class in tool_classes:
                    param_info = self._extract_parameters(tool_class)
                    tool_info = {
                        'name': tool_class.__name__,
                        'type': tool_type,
                        'file': file_path,
                        'description': getattr(tool_class, '__doc__', ''),
                        'parameters': param_info,
                        'has_parameter_descriptions': hasattr(tool_class, '_parameter_descriptions')
                    }
                    all_tools.append(tool_info)
            
            return all_tools
            
        except Exception as e:
            print(f"Warning: Failed to scan plugin {file_path}: {e}")
            return []
    
    def _file_path_to_module_path(self, file_path: str) -> Optional[str]:
        """将文件路径转换为模块路径"""
        try:
            # 移除 .py 扩展名
            if file_path.endswith('.py'):
                file_path = file_path[:-3]
            
            # 替换路径分隔符
            module_path = file_path.replace('/', '.').replace('\\', '.')
            
            # 移除开头的点
            if module_path.startswith('.'):
                module_path = module_path[1:]
            
            return module_path
        except:
            return None
    
    def _find_tool_class(self, module, tool_type: str):
        """在模块中查找工具类"""
        tool_base_classes = {
            'attack': ['BaseAttack'],
            'metric': ['BaseRedTeamingMetric'],
            'vulnerability': ['BaseVulnerability']
        }
        
        base_classes = tool_base_classes.get(tool_type, [])
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if inspect.isclass(attr):
                # 检查是否继承自工具基类
                for base_class_name in base_classes:
                    try:
                        # 获取基类
                        base_class = getattr(module, base_class_name, None)
                        if base_class and issubclass(attr, base_class) and attr != base_class:
                            return attr
                    except:
                        continue
                
                # 检查模块的基类
                for base_class_name in base_classes:
                    try:
                        # 尝试从其他模块导入基类
                        if tool_type == 'attack':
                            from deepteam.attacks.base_attack import BaseAttack
                            if issubclass(attr, BaseAttack) and attr != BaseAttack:
                                return attr
                        elif tool_type == 'metric':
                            from deepteam.metrics.base_red_teaming_metric import BaseRedTeamingMetric
                            if issubclass(attr, BaseRedTeamingMetric) and attr != BaseRedTeamingMetric:
                                return attr
                        elif tool_type == 'vulnerability':
                            from deepteam.vulnerabilities.base_vulnerability import BaseVulnerability
                            if issubclass(attr, BaseVulnerability) and attr != BaseVulnerability:
                                return attr
                    except:
                        continue
        
        return None
    
    def _find_all_tool_classes(self, module, tool_type: str) -> List:
        """在模块中查找所有工具类"""
        tool_classes = []
        tool_base_classes = {
            'attack': ['BaseAttack'],
            'metric': ['BaseRedTeamingMetric'],
            'vulnerability': ['BaseVulnerability']
        }
        
        base_classes = tool_base_classes.get(tool_type, [])
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if inspect.isclass(attr):
                # 检查是否继承自工具基类
                for base_class_name in base_classes:
                    try:
                        # 获取基类
                        base_class = getattr(module, base_class_name, None)
                        if base_class and issubclass(attr, base_class) and attr != base_class:
                            tool_classes.append(attr)
                            break
                    except:
                        continue
                
                # 检查模块的基类
                for base_class_name in base_classes:
                    try:
                        # 尝试从其他模块导入基类
                        if tool_type == 'attack':
                            from deepteam.attacks.base_attack import BaseAttack
                            if issubclass(attr, BaseAttack) and attr != BaseAttack:
                                tool_classes.append(attr)
                                break
                        elif tool_type == 'metric':
                            from deepteam.metrics.base_red_teaming_metric import BaseRedTeamingMetric
                            if issubclass(attr, BaseRedTeamingMetric) and attr != BaseRedTeamingMetric:
                                tool_classes.append(attr)
                                break
                        elif tool_type == 'vulnerability':
                            from deepteam.vulnerabilities.base_vulnerability import BaseVulnerability
                            if issubclass(attr, BaseVulnerability) and attr != BaseVulnerability:
                                tool_classes.append(attr)
                                break
                    except:
                        continue
        
        return tool_classes
    
    def _extract_parameters(self, tool_class) -> Dict[str, Any]:
        """提取工具类的参数信息"""
        parameters = {}
        
        try:
            # 获取 __init__ 方法的参数
            init_sig = inspect.signature(tool_class.__init__)
            
            for param_name, param in init_sig.parameters.items():
                if param_name == 'self':
                    continue
                    
                param_info = {
                    'required': param.default == inspect.Parameter.empty,
                    'default': param.default if param.default != inspect.Parameter.empty else None,
                    'description': ''
                }
                
                # 从装饰器中获取参数描述
                if hasattr(tool_class, '_parameter_descriptions'):
                    param_info['description'] = tool_class._parameter_descriptions.get(param_name, '')
                
                parameters[param_name] = param_info
        except Exception as e:
            print(f"Warning: Failed to extract parameters from {tool_class.__name__}: {e}")
        
        return parameters
    
    def validate_tool_completeness(self) -> List[str]:
        """验证工具参数说明的完整性"""
        warnings = []
        for tool_name, tool_info in self.tools_info.items():
            if not tool_info['has_parameter_descriptions']:
                warnings.append(f"Warning: {tool_name} 缺少参数说明装饰器")
            else:
                # 检查是否所有参数都有描述
                for param_name, param_info in tool_info['parameters'].items():
                    if not param_info['description']:
                        warnings.append(f"Warning: {tool_name}.{param_name} 缺少参数描述")
        
        return warnings
    
    def get_tools_by_type(self, tool_type: str) -> Dict[str, Any]:
        """获取指定类型的工具"""
        return {name: info for name, info in self.tools_info.items() 
                if info['type'] == tool_type}
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取指定工具的详细信息"""
        return self.tools_info.get(tool_name) 