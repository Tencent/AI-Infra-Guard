import inspect
import ast
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import importlib.util
from loguru import logger

from deepteam.attacks import BaseAttack
from deepteam.metrics import BaseRedTeamingMetric
from deepteam.vulnerabilities import BaseVulnerability


class PluginValidator:
    """验证用户上传的算子插件是否符合系统要求"""
    
    def __init__(self):
        self.required_base_classes = {
            'attack': BaseAttack,
            'metric': BaseRedTeamingMetric,
            'vulnerability': BaseVulnerability
        }
        
        self.required_methods = {
            'attack': ['enhance', 'get_name'],
            'metric': ['measure', 'get_name'],
            'vulnerability': ['get_name', 'get_types']
        }
    
    def validate_plugin_file(self, file_path: Path) -> Dict[str, Any]:
        """验证单个插件文件"""
        result = {
            'valid': False,
            'plugin_type': None,
            'class_name': None,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 检查文件扩展名
            if file_path.suffix != '.py':
                result['errors'].append(f"文件必须是Python文件 (.py): {file_path}")
                return result
            
            # 解析Python文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用AST解析文件
            tree = ast.parse(content)
            
            # 查找类定义
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            
            if not classes:
                result['errors'].append("文件中没有找到类定义")
                return result
            
            # 检查每个类
            for class_node in classes:
                class_result = self._validate_class(class_node, content, file_path)
                if class_result['valid']:
                    result.update(class_result)
                    break
            else:
                result['errors'].append("没有找到符合要求的类")
                
        except Exception as e:
            result['errors'].append(f"验证过程中发生错误: {str(e)}")
        
        return result
    
    def _validate_class(self, class_node: ast.ClassDef, content: str, file_path: Path) -> Dict[str, Any]:
        """验证单个类是否符合插件要求"""
        result = {
            'valid': False,
            'plugin_type': None,
            'class_name': class_node.name,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 检查类是否继承自正确的基类
            base_classes = self._get_base_classes(class_node)
            
            # 确定插件类型
            plugin_type = None
            for base_class_name in base_classes:
                if 'Attack' in base_class_name or 'attack' in base_class_name.lower():
                    plugin_type = 'attack'
                    break
                elif 'Metric' in base_class_name or 'metric' in base_class_name.lower():
                    plugin_type = 'metric'
                    break
                elif 'Vulnerability' in base_class_name or 'vulnerability' in base_class_name.lower():
                    plugin_type = 'vulnerability'
                    break
            
            if not plugin_type:
                # 尝试动态导入验证
                plugin_type = self._dynamic_validate_class(file_path, class_node.name)
            
            if not plugin_type:
                result['errors'].append(f"类 {class_node.name} 没有继承正确的基类")
                return result
            
            result['plugin_type'] = plugin_type
            
            # 检查必需的方法
            required_methods = self.required_methods[plugin_type]
            class_methods = [node.name for node in class_node.body if isinstance(node, ast.FunctionDef)]
            
            missing_methods = []
            for method in required_methods:
                if method not in class_methods:
                    missing_methods.append(method)
            
            if missing_methods:
                result['errors'].append(f"缺少必需的方法: {', '.join(missing_methods)}")
                return result
            
            # 检查是否有抽象方法
            has_abstract_methods = self._check_abstract_methods(class_node)
            if has_abstract_methods:
                result['warnings'].append("类包含抽象方法，需要实现")
            
            result['valid'] = True
            
        except Exception as e:
            result['errors'].append(f"验证类时发生错误: {str(e)}")
        
        return result
    
    def _get_base_classes(self, class_node: ast.ClassDef) -> List[str]:
        """获取类的基类名称"""
        base_classes = []
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                # 处理类似 module.Class 的情况
                base_classes.append(self._get_attribute_name(base))
        return base_classes
    
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """获取属性访问的完整名称"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        else:
            return node.attr
    
    def _check_abstract_methods(self, class_node: ast.ClassDef) -> bool:
        """检查类是否包含抽象方法"""
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                # 检查是否有 @abstractmethod 装饰器
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'abstractmethod':
                        return True
                    elif isinstance(decorator, ast.Attribute) and decorator.attr == 'abstractmethod':
                        return True
        return False
    
    def _dynamic_validate_class(self, file_path: Path, class_name: str) -> Optional[str]:
        """动态导入验证类"""
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location("temp_module", file_path)
            if spec is None:
                return None
                
            module = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                return None
                
            spec.loader.exec_module(module)
            
            # 获取类
            cls = getattr(module, class_name, None)
            if not cls:
                return None
            
            # 检查继承关系
            if issubclass(cls, BaseAttack):
                return 'attack'
            elif issubclass(cls, BaseRedTeamingMetric):
                return 'metric'
            elif issubclass(cls, BaseVulnerability):
                return 'vulnerability'
            
        except Exception as e:
            logger.warning(f"动态验证失败: {e}")
        
        return None
    
    def validate_plugin_directory(self, dir_path: Path) -> Dict[str, Any]:
        """验证插件目录"""
        result = {
            'valid': False,
            'plugins': [],
            'errors': [],
            'warnings': []
        }
        
        if not dir_path.exists() or not dir_path.is_dir():
            result['errors'].append(f"目录不存在或不是有效目录: {dir_path}")
            return result
        
        # 查找所有Python文件
        py_files = list(dir_path.glob("*.py"))
        
        if not py_files:
            result['errors'].append(f"目录中没有找到Python文件: {dir_path}")
            return result
        
        # 验证每个文件
        for py_file in py_files:
            file_result = self.validate_plugin_file(py_file)
            if file_result['valid']:
                result['plugins'].append(file_result)
            else:
                result['errors'].extend([f"{py_file.name}: {error}" for error in file_result['errors']])
                result['warnings'].extend([f"{py_file.name}: {warning}" for warning in file_result['warnings']])
        
        result['valid'] = len(result['plugins']) > 0
        
        return result 