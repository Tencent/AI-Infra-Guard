import os
import importlib
import ast
from typing import List, Any, Tuple
from deepteam.plugin_system import PluginManager
from cli.aig_logger import logger
from cli.aig_logger import (
    newPlanStep, statusUpdate, toolUsed, actionLog, resultUpdate
)
from .mappings import TECHNIQUE_CLASS_MAP, SCENARIO_CLASS_MAP, METRIC_CLASS_MAP


def dynamic_import(class_path: str) -> Any:
    """动态导入类"""
    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def parse_kwargs(param_str: str) -> dict:
    """解析参数字符串为字典"""
    kwargs = {}
    
    # 特殊处理 prompt 参数，直接传递整个字符串
    if param_str.startswith("prompt="):
        prompt_value = param_str[7:]  # 去掉 "prompt="
        kwargs["prompt"] = prompt_value
        return kwargs
    
    # 处理其他参数
    params = []
    buf = ''
    bracket_level = 0
    for c in param_str:
        if c == '[':
            bracket_level += 1
        elif c == ']':
            bracket_level -= 1
        if c == ',' and bracket_level == 0:
            params.append(buf)
            buf = ''
        else:
            buf += c
    if buf:
        params.append(buf)
    
    for kv in params:
        if "=" in kv:
            k, v = kv.split("=", 1)
            v = v.strip()
            try:
                v_eval = ast.literal_eval(v)
                kwargs[k.strip()] = v_eval
            except Exception:
                kwargs[k.strip()] = v
    return kwargs


def parse_metric_class(arg: str) -> Tuple[str | None, str | None]:
    """解析指标类名"""
    if not arg:
        return None
    if ":" in arg:
        class_name, param_str = arg.split(":", 1)
        kwargs = parse_kwargs(param_str)
    else:
        class_name = arg
        kwargs = None
    return METRIC_CLASS_MAP.get(class_name, class_name), kwargs


def parse_attack(arg: str, plugin_manager: PluginManager) -> Any:
    """解析攻击参数"""
    if ":" in arg:
        class_name, param_str = arg.split(":", 1)
        
        # 首先检查是否是自定义插件
        custom_attack = plugin_manager.create_attack_instance(class_name)
        if custom_attack:
            kwargs = parse_kwargs(param_str)
            return custom_attack.__class__(**kwargs)
        
        # 如果不是自定义插件，使用内置映射
        class_path = TECHNIQUE_CLASS_MAP.get(class_name)
        if not class_path:
            raise ValueError(f"未知的攻击类型: {class_name}")
            
        cls = dynamic_import(class_path)
        kwargs = parse_kwargs(param_str)
        return cls(**kwargs)
    else:
        class_name = arg
        
        # 首先检查是否是自定义插件
        custom_attack = plugin_manager.create_attack_instance(class_name)
        if custom_attack:
            return custom_attack
        
        # 如果不是自定义插件，使用内置映射
        class_path = TECHNIQUE_CLASS_MAP.get(class_name)
        if not class_path:
            raise ValueError(f"未知的攻击类型: {class_name}")
            
        cls = dynamic_import(class_path)
        # 为不同攻击方法设置不同权重，确保均衡使用
        if class_name == "PromptInjection":
            return cls(weight=1)
        elif class_name == "Roleplay":
            return cls(weight=1)
        elif class_name == "Base64":
            return cls(weight=1)
        else:
            return cls()


def parse_vulnerability(arg: str, plugin_manager: PluginManager):
    """解析漏洞参数"""
    if ":" in arg:
        class_name, param_str = arg.split(":", 1)
        
        # 首先检查是否是自定义插件
        custom_vulnerability = plugin_manager.create_vulnerability_instance(class_name)
        if custom_vulnerability:
            kwargs = parse_kwargs(param_str)
            return [custom_vulnerability.__class__(**kwargs)]
        
        if class_name == "Custom":
            from deepteam.vulnerabilities import CustomPrompt
            kwargs = parse_kwargs(param_str)
            logger.debug(f"Creating CustomPrompt with kwargs: {kwargs}")
            
            # 为每个prompt创建独立的CustomPrompt对象
            if 'prompt' in kwargs:
                prompt_value = kwargs['prompt']
                if isinstance(prompt_value, str):
                    return [CustomPrompt(**kwargs)], prompt_value
            elif 'prompt_file' in kwargs:
                # 处理prompt_file参数，为每个prompt创建独立的vulnerability对象
                prompt_file = kwargs['prompt_file']
                # 先创建一个临时的CustomPrompt来获取prompts和元数据
                temp_vuln = CustomPrompt(prompt_file=prompt_file)
                prompts = temp_vuln.prompts
                metadata = temp_vuln.metadata
                
                vulnerabilities = []
                for i, (prompt, meta) in enumerate(zip(prompts, metadata)):
                    vuln = CustomPrompt(prompt=prompt)
                    # 使用元数据中的信息来命名vulnerability（仅对文件输入）
                    category = meta.get('category', 'custom')
                    language = meta.get('language', 'unknown')
                    vuln.name = f"Custom Prompt {i+1} ({category}-{language})"
                    vulnerabilities.append(vuln)
                return vulnerabilities, os.path.basename(prompt_file)
            else:
                return [CustomPrompt(**kwargs)], None
        elif class_name == "MultiDataset":
            from deepteam.vulnerabilities import MultiDatasetVulnerability
            kwargs = parse_kwargs(param_str)
            logger.debug(f"Creating MultiDatasetVulnerability with kwargs: {kwargs}")
            
            # 处理MultiDatasetVulnerability的特殊参数
            dataset_file = kwargs.get('dataset_file', 'jailbreak_prompts_top.json')
            num_prompts = kwargs.get('num_prompts', 10)
            random_seed = kwargs.get('random_seed')
            prompt_column = kwargs.get('prompt_column')
            filter_conditions = kwargs.get('filter_conditions')
            
            # 创建MultiDatasetVulnerability对象
            vuln = MultiDatasetVulnerability(
                dataset_file=dataset_file,
                num_prompts=num_prompts,
                random_seed=random_seed,
                prompt_column=prompt_column,
                filter_conditions=filter_conditions
            )
            
            # 为每个prompt创建独立的vulnerability对象
            vulnerabilities = []
            for i, prompt in enumerate(vuln.prompts):
                # 创建新的MultiDatasetVulnerability实例，但只包含单个prompt
                single_vuln = MultiDatasetVulnerability(
                    prompt=prompt,
                )
                
                # 使用元数据中的信息来命名vulnerability
                if i < len(vuln.metadata):
                    meta = vuln.metadata[i]
                    single_vuln.metadata = [meta]
                    category = meta.get('category', 'multi_dataset')
                    language = meta.get('language', 'unknown')
                    source_file = meta.get('source_file', 'unknown')
                    single_vuln.name = f"MultiDataset Vulnerability {i+1} ({category}-{language}-{source_file})"
                else:
                    single_vuln.name = f"MultiDataset Vulnerability {i+1}"
                
                vulnerabilities.append(single_vuln)
            
            return vulnerabilities, os.path.basename(dataset_file)
        else:
            # 如果不是自定义插件，使用内置映射
            class_path = SCENARIO_CLASS_MAP.get(class_name)
            if not class_path:
                raise ValueError(f"未知的漏洞类型: {class_name}")
                
            cls = dynamic_import(class_path)
            kwargs = parse_kwargs(param_str)
            return [cls(**kwargs)], None
    else:
        class_name = arg
        
        # 首先检查是否是自定义插件
        custom_vulnerability = plugin_manager.create_vulnerability_instance(class_name)
        if custom_vulnerability:
            return [custom_vulnerability], None
        
        if class_name == "Custom":
            from deepteam.vulnerabilities import CustomPrompt
            return [CustomPrompt()], None
        elif class_name == "MultiDataset":
            from deepteam.vulnerabilities import MultiDatasetVulnerability
            return [MultiDatasetVulnerability()], None
        else:
            # 如果不是自定义插件，使用内置映射
            class_path = SCENARIO_CLASS_MAP.get(class_name)
            if not class_path:
                raise ValueError(f"未知的漏洞类型: {class_name}")
                
            cls = dynamic_import(class_path)
            return [cls()], None
