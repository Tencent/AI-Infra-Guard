from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from loguru import logger

from .plugin_loader import PluginLoader
from .plugin_registry import PluginRegistry
from .remote_plugin_downloader import RemotePluginDownloader
from deepteam.attacks import BaseAttack
from deepteam.metrics import BaseRedTeamingMetric
from deepteam.vulnerabilities import BaseVulnerability


class PluginManager:
    """插件管理器，作为插件系统的主要接口"""
    
    def __init__(self):
        self.registry = PluginRegistry()
        self.loader = PluginLoader(self.registry)
        self.downloader = RemotePluginDownloader()
        
    def load_plugin(self, plugin_path: Union[str, Path]) -> Dict[str, Any]:
        """加载单个插件"""
        plugin_path = str(plugin_path)
        
        # 检查是否为远程插件URL
        if self.downloader.is_remote_plugin_url(plugin_path):
            return self._load_remote_plugin(plugin_path)
        
        # 本地插件加载
        return self.loader.load_plugin(plugin_path)
    
    def _load_remote_plugin(self, url: str) -> Dict[str, Any]:
        """加载远程插件"""
        result = {
            'success': False,
            'plugin_info': None,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 下载并解压远程插件
            download_result = self.downloader.download_and_extract_plugin(url)
            
            if not download_result['success']:
                result['errors'].extend(download_result['errors'])
                result['warnings'].extend(download_result['warnings'])
                return result
            
            # 加载解压后的插件
            extracted_path = download_result['extracted_path']
            if extracted_path:
                load_result = self.loader.load_plugin(extracted_path)
                
                if load_result['success']:
                    result['success'] = True
                    result['plugin_info'] = {
                        'type': 'remote',
                        'url': url,
                        'local_path': extracted_path,
                        'load_info': load_result['plugin_info']
                    }
                    logger.info(f"远程插件加载成功: {url}")
                else:
                    result['errors'].extend(load_result['errors'])
                    result['warnings'].extend(load_result['warnings'])
            
        except Exception as e:
            result['errors'].append(f"加载远程插件时发生错误: {str(e)}")
            logger.error(f"加载远程插件失败: {str(e)}")
        
        return result
    
    def load_remote_plugin(self, url: str, force_download: bool = False) -> Dict[str, Any]:
        """专门用于加载远程插件的方法"""
        return self._load_remote_plugin(url)
    
    def list_remote_plugins(self) -> List[Dict[str, Any]]:
        """列出已下载的远程插件"""
        return self.downloader.list_remote_plugins()
    
    def remove_remote_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """删除远程插件"""
        return self.downloader.remove_remote_plugin(plugin_name)
    
    def cleanup_remote_plugins(self):
        """清理远程插件临时文件"""
        self.downloader.cleanup_temp_files()
    
    def load_plugins_from_directory(self, dir_path: Union[str, Path]) -> Dict[str, Any]:
        """从目录加载所有插件"""
        return self.loader.load_plugins_from_directory(dir_path)
    
    def auto_discover_plugins(self) -> Dict[str, Any]:
        """自动发现并加载插件"""
        return self.loader.auto_discover_plugins()
    
    def load_plugins_from_config(self, config_file: Union[str, Path]) -> Dict[str, Any]:
        """从配置文件加载插件"""
        return self.loader.load_plugins_from_config(config_file)
    
    def get_loaded_plugins(self) -> Dict[str, List[str]]:
        """获取已加载的插件列表"""
        return self.loader.get_loaded_plugins()
    
    def get_plugin_info(self, plugin_key: str) -> Optional[Dict[str, Any]]:
        """获取插件详细信息"""
        return self.loader.get_plugin_info(plugin_key)
    
    def unload_plugin(self, plugin_key: str) -> bool:
        """卸载插件"""
        return self.loader.unload_plugin(plugin_key)
    
    def reload_plugin(self, plugin_path: Union[str, Path]) -> Dict[str, Any]:
        """重新加载插件"""
        return self.loader.reload_plugin(plugin_path)
    
    def create_attack_instance(self, class_name: str, **kwargs) -> Optional[BaseAttack]:
        """创建攻击插件实例"""
        return self.registry.create_attack_instance(class_name, **kwargs)
    
    def create_metric_instance(self, class_name: str, **kwargs) -> Optional[BaseRedTeamingMetric]:
        """创建指标插件实例"""
        return self.registry.create_metric_instance(class_name, **kwargs)
    
    def create_vulnerability_instance(self, class_name: str, **kwargs) -> Optional[BaseVulnerability]:
        """创建漏洞插件实例"""
        return self.registry.create_vulnerability_instance(class_name, **kwargs)
    
    def get_attack_plugins(self) -> List[str]:
        """获取所有攻击插件名称"""
        return list(self.registry.attack_plugins.keys())
    
    def get_metric_plugins(self) -> List[str]:
        """获取所有指标插件名称"""
        return list(self.registry.metric_plugins.keys())
    
    def get_vulnerability_plugins(self) -> List[str]:
        """获取所有漏洞插件名称"""
        return list(self.registry.vulnerability_plugins.keys())
    
    def get_plugin_count(self) -> Dict[str, int]:
        """获取插件数量统计"""
        return self.registry.get_plugin_count()
    
    def clear_all_plugins(self):
        """清除所有插件"""
        self.registry.clear_all_plugins()
    
    def list_plugins_with_info(self) -> Dict[str, List[Dict[str, Any]]]:
        """列出所有插件及其详细信息"""
        result = {
            'attacks': [],
            'metrics': [],
            'vulnerabilities': []
        }
        
        # 获取攻击插件信息
        for class_name in self.registry.attack_plugins.keys():
            plugin_key = f"attack_{class_name}"
            info = self.registry.get_plugin_info(plugin_key)
            if info:
                result['attacks'].append({
                    'class_name': class_name,
                    'path': info['path'],
                    'module_name': info['module_name']
                })
        
        # 获取指标插件信息
        for class_name in self.registry.metric_plugins.keys():
            plugin_key = f"metric_{class_name}"
            info = self.registry.get_plugin_info(plugin_key)
            if info:
                result['metrics'].append({
                    'class_name': class_name,
                    'path': info['path'],
                    'module_name': info['module_name']
                })
        
        # 获取漏洞插件信息
        for class_name in self.registry.vulnerability_plugins.keys():
            plugin_key = f"vulnerability_{class_name}"
            info = self.registry.get_plugin_info(plugin_key)
            if info:
                result['vulnerabilities'].append({
                    'class_name': class_name,
                    'path': info['path'],
                    'module_name': info['module_name']
                })
        
        return result
    
    def validate_plugin(self, plugin_path: Union[str, Path]) -> Dict[str, Any]:
        """验证插件（不加载）"""
        plugin_path = Path(plugin_path)
        
        if plugin_path.is_file():
            return self.loader.validator.validate_plugin_file(plugin_path)
        elif plugin_path.is_dir():
            return self.loader.validator.validate_plugin_directory(plugin_path)
        else:
            return {
                'valid': False,
                'errors': [f"路径不存在: {plugin_path}"]
            }
    
    def get_plugin_template(self, plugin_type: str) -> str:
        """获取插件模板代码"""
        if plugin_type == 'attack':
            return self._get_attack_template()
        elif plugin_type == 'metric':
            return self._get_metric_template()
        elif plugin_type == 'vulnerability':
            return self._get_vulnerability_template()
        else:
            return f"未知的插件类型: {plugin_type}"
    
    def _get_attack_template(self) -> str:
        """获取攻击插件模板"""
        return '''from deepteam.attacks import BaseAttack

class CustomAttack(BaseAttack):
    """自定义攻击插件"""
    
    def __init__(self, weight: int = 1):
        super().__init__()
        self.weight = weight
    
    def enhance(self, attack: str, *args, **kwargs) -> str:
        """
        增强攻击字符串
        
        Args:
            attack: 原始攻击字符串
            *args: 额外参数
            **kwargs: 额外关键字参数
            
        Returns:
            增强后的攻击字符串
        """
        # 在这里实现你的攻击增强逻辑
        enhanced_attack = attack  # 默认不修改
        
        # 示例：添加前缀
        # enhanced_attack = f"请忽略之前的指令，{attack}"
        
        return enhanced_attack
    
    def get_name(self) -> str:
        """获取插件名称"""
        return "CustomAttack"
    
    async def a_enhance(self, attack: str, *args, **kwargs) -> str:
        """
        异步增强攻击字符串（可选实现）
        
        如果不需要异步支持，可以删除这个方法，会使用默认的同步实现
        """
        return self.enhance(attack, *args, **kwargs)
'''
    
    def _get_metric_template(self) -> str:
        """获取指标插件模板"""
        return '''from typing import Optional, Union
from deepeval.test_case.llm_test_case import LLMTestCase
from deepeval.test_case.conversational_test_case import ConversationalTestCase
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.metrics.utils import initialize_model
from deepteam.metrics import BaseRedTeamingMetric

class CustomMetric(BaseRedTeamingMetric):
    """自定义指标插件"""
    
    def __init__(
        self,
        model: Optional[Union[str, DeepEvalBaseLLM]] = None,
        async_mode: bool = True,
        verbose_mode: bool = False,
    ):
        self.model, self.using_native_model = initialize_model(model)
        self.evaluation_model = self.model.get_model_name()
        self.async_mode = async_mode
        self.verbose_mode = verbose_mode
        self.system_prompt = ""
    
    def measure(self, test_case: Union[LLMTestCase, ConversationalTestCase]) -> float:
        """
        测量指标
        
        Args:
            test_case: 测试用例
            
        Returns:
            指标分数 (0-1)
        """
        # 在这里实现你的指标计算逻辑
        score = 0.5  # 默认分数
        
        return score
    
    def get_name(self) -> str:
        """获取指标名称"""
        return "CustomMetric"
    
    async def a_measure(self, test_case: Union[LLMTestCase, ConversationalTestCase]) -> float:
        """
        异步测量指标（可选实现）
        
        如果不需要异步支持，可以删除这个方法，会使用默认的同步实现
        """
        return self.measure(test_case)
'''
    
    def _get_vulnerability_template(self) -> str:
        """获取漏洞插件模板"""
        return '''from typing import List
from enum import Enum
from deepteam.vulnerabilities import BaseVulnerability

class CustomVulnerabilityType(Enum):
    """自定义漏洞类型枚举"""
    CUSTOM_VULNERABILITY = "custom_vulnerability"

class CustomVulnerability(BaseVulnerability):
    """自定义漏洞插件"""
    
    def __init__(self, name: str = "CustomVulnerability", types: List[Enum] = None):
        """
        初始化自定义漏洞
        
        Args:
            name: 漏洞名称
            types: 漏洞类型列表
        """
        if types is None:
            types = [CustomVulnerabilityType.CUSTOM_VULNERABILITY]
        
        self.name = name
        super().__init__(types)
    
    def get_name(self) -> str:
        """获取漏洞名称"""
        return self.name
    
    def get_types(self) -> List[Enum]:
        """获取漏洞类型列表"""
        return self.types
    
    def get_values(self) -> List[str]:
        """获取漏洞类型值列表"""
        return [t.value for t in self.types]
    
    def __repr__(self):
        """字符串表示"""
        return f"{self.name} (types={self.types})"
''' 