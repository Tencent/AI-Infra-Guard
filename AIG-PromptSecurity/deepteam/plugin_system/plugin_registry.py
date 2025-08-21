from typing import Dict, List, Optional, Any, Type
from pathlib import Path
import importlib.util
import sys
from loguru import logger

from deepteam.attacks import BaseAttack
from deepteam.metrics import BaseRedTeamingMetric
from deepteam.vulnerabilities import BaseVulnerability


class PluginRegistry:
    """插件注册表，管理已加载的插件"""
    
    def __init__(self):
        self.attack_plugins: Dict[str, Type[BaseAttack]] = {}
        self.metric_plugins: Dict[str, Type[BaseRedTeamingMetric]] = {}
        self.vulnerability_plugins: Dict[str, Type[BaseVulnerability]] = {}
        self.plugin_metadata: Dict[str, Dict[str, Any]] = {}
        self.loaded_modules: Dict[str, Any] = {}
    
    def register_plugin(self, plugin_path: Path, plugin_info: Dict[str, Any]) -> bool:
        """注册插件"""
        try:
            plugin_type = plugin_info['plugin_type']
            class_name = plugin_info['class_name']
            
            # 动态加载模块
            module_name = f"custom_plugin_{plugin_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            
            if spec is None:
                logger.error(f"无法创建模块规范: {plugin_path}")
                return False
                
            module = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                logger.error(f"模块加载器为空: {plugin_path}")
                return False
                
            spec.loader.exec_module(module)
            
            # 获取类
            plugin_class = getattr(module, class_name, None)
            if not plugin_class:
                logger.error(f"在模块中找不到类 {class_name}: {plugin_path}")
                return False
            
            # 验证类类型
            if plugin_type == 'attack' and not issubclass(plugin_class, BaseAttack):
                logger.error(f"类 {class_name} 不是有效的攻击插件")
                return False
            elif plugin_type == 'metric' and not issubclass(plugin_class, BaseRedTeamingMetric):
                logger.error(f"类 {class_name} 不是有效的指标插件")
                return False
            elif plugin_type == 'vulnerability' and not issubclass(plugin_class, BaseVulnerability):
                logger.error(f"类 {class_name} 不是有效的漏洞插件")
                return False
            
            # 注册插件
            plugin_key = f"{plugin_type}_{class_name}"
            
            if plugin_type == 'attack':
                self.attack_plugins[class_name] = plugin_class  # type: ignore
            elif plugin_type == 'metric':
                self.metric_plugins[class_name] = plugin_class  # type: ignore
            elif plugin_type == 'vulnerability':
                self.vulnerability_plugins[class_name] = plugin_class  # type: ignore
            
            # 保存元数据
            self.plugin_metadata[plugin_key] = {
                'path': str(plugin_path),
                'type': plugin_type,
                'class_name': class_name,
                'module_name': module_name,
                'info': plugin_info
            }
            
            # 保存模块引用
            self.loaded_modules[module_name] = module
            
            logger.info(f"成功注册插件: {plugin_key}")
            return True
            
        except Exception as e:
            logger.error(f"注册插件失败 {plugin_path}: {e}")
            return False
    
    def get_attack_plugin(self, class_name: str) -> Optional[Type[BaseAttack]]:
        """获取攻击插件类"""
        return self.attack_plugins.get(class_name)
    
    def get_metric_plugin(self, class_name: str) -> Optional[Type[BaseRedTeamingMetric]]:
        """获取指标插件类"""
        return self.metric_plugins.get(class_name)
    
    def get_vulnerability_plugin(self, class_name: str) -> Optional[Type[BaseVulnerability]]:
        """获取漏洞插件类"""
        return self.vulnerability_plugins.get(class_name)
    
    def create_attack_instance(self, class_name: str, **kwargs) -> Optional[BaseAttack]:
        """创建攻击插件实例"""
        plugin_class = self.get_attack_plugin(class_name)
        if plugin_class:
            try:
                return plugin_class(**kwargs)
            except Exception as e:
                logger.error(f"创建攻击插件实例失败 {class_name}: {e}")
        return None
    
    def create_metric_instance(self, class_name: str, **kwargs) -> Optional[BaseRedTeamingMetric]:
        """创建指标插件实例"""
        plugin_class = self.get_metric_plugin(class_name)
        if plugin_class:
            try:
                return plugin_class(**kwargs)
            except Exception as e:
                logger.error(f"创建指标插件实例失败 {class_name}: {e}")
        return None
    
    def create_vulnerability_instance(self, class_name: str, **kwargs) -> Optional[BaseVulnerability]:
        """创建漏洞插件实例"""
        plugin_class = self.get_vulnerability_plugin(class_name)
        if plugin_class:
            try:
                return plugin_class(**kwargs)
            except Exception as e:
                logger.error(f"创建漏洞插件实例失败 {class_name}: {e}")
        return None
    
    def list_plugins(self) -> Dict[str, List[str]]:
        """列出所有已注册的插件"""
        return {
            'attacks': list(self.attack_plugins.keys()),
            'metrics': list(self.metric_plugins.keys()),
            'vulnerabilities': list(self.vulnerability_plugins.keys())
        }
    
    def get_plugin_info(self, plugin_key: str) -> Optional[Dict[str, Any]]:
        """获取插件信息"""
        return self.plugin_metadata.get(plugin_key)
    
    def unregister_plugin(self, plugin_key: str) -> bool:
        """注销插件"""
        try:
            if plugin_key in self.plugin_metadata:
                info = self.plugin_metadata[plugin_key]
                plugin_type = info['type']
                class_name = info['class_name']
                
                # 从注册表中移除
                if plugin_type == 'attack' and class_name in self.attack_plugins:
                    del self.attack_plugins[class_name]
                elif plugin_type == 'metric' and class_name in self.metric_plugins:
                    del self.metric_plugins[class_name]
                elif plugin_type == 'vulnerability' and class_name in self.vulnerability_plugins:
                    del self.vulnerability_plugins[class_name]
                
                # 移除模块引用
                module_name = info['module_name']
                if module_name in self.loaded_modules:
                    del self.loaded_modules[module_name]
                
                # 移除元数据
                del self.plugin_metadata[plugin_key]
                
                logger.info(f"成功注销插件: {plugin_key}")
                return True
                
        except Exception as e:
            logger.error(f"注销插件失败 {plugin_key}: {e}")
        
        return False
    
    def clear_all_plugins(self):
        """清除所有插件"""
        self.attack_plugins.clear()
        self.metric_plugins.clear()
        self.vulnerability_plugins.clear()
        self.plugin_metadata.clear()
        self.loaded_modules.clear()
        logger.info("已清除所有插件")
    
    def get_plugin_count(self) -> Dict[str, int]:
        """获取插件数量统计"""
        return {
            'attacks': len(self.attack_plugins),
            'metrics': len(self.metric_plugins),
            'vulnerabilities': len(self.vulnerability_plugins),
            'total': len(self.plugin_metadata)
        } 