"""
LLM管理器 - 管理多个专用LLM实例
"""
from typing import Dict, Optional
from utils.llm import LLM
from utils.logging import logger
from utils import config


class LLMManager:
    """管理多个专用LLM实例，支持不同用途的模型配置"""
    
    # 预定义的模型配置（从环境变量读取）
    DEFAULT_CONFIGS = {
        "default": {
            "model": config.DEFAULT_MODEL,
            "base_url": config.DEFAULT_BASE_URL,
            "description": "默认模型"
        },
        "thinking": {
            "model": config.THINKING_MODEL,
            "base_url": config.THINKING_BASE_URL,
            "api_key": config.THINKING_API_KEY,  # 可选，为 None 时使用主 API Key
            "description": "专门用于深度思考和推理的模型"
        },
        "coding": {
            "model": config.CODING_MODEL,
            "base_url": config.CODING_BASE_URL,
            "api_key": config.CODING_API_KEY,  # 可选，为 None 时使用主 API Key
            "description": "专门用于代码生成和分析的模型"
        },
        "fast": {
            "model": config.FAST_MODEL,
            "base_url": config.FAST_BASE_URL,
            "api_key": config.FAST_API_KEY,  # 可选，为 None 时使用主 API Key
            "description": "用于快速响应的轻量级模型"
        },
    }
    
    def __init__(self, api_key: str, base_url: str = None):
        """
        初始化LLM管理器
        
        Args:
            api_key: 主 API 密钥（作为默认值）
            base_url: 主 API 基础URL（作为默认值，如果不提供则使用 config.DEFAULT_BASE_URL）
        """
        self.default_api_key = api_key
        self.default_base_url = base_url or config.DEFAULT_BASE_URL
        self._llm_instances: Dict[str, LLM] = {}
        self._custom_configs: Dict[str, dict] = {}
    
    def configure(
        self, 
        purpose: str, 
        model: str, 
        temperature: float = 0.7,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> None:
        """
        配置特定用途的模型
        
        Args:
            purpose: 用途标识（如 "thinking", "coding"）
            model: 模型名称
            temperature: 温度参数
            base_url: API 基础 URL（可选，不提供则使用默认）
            api_key: API 密钥（可选，不提供则使用默认）
        """
        self._custom_configs[purpose] = {
            "model": model,
            "temperature": temperature,
            "base_url": base_url,
            "api_key": api_key
        }
        
        # 清除已有实例，下次获取时重新创建
        if purpose in self._llm_instances:
            del self._llm_instances[purpose]
        
        logger.info(f"Configured LLM for purpose '{purpose}': {model}")
    
    def get_llm(self, purpose: str = "default") -> Optional[LLM]:
        """
        获取指定用途的LLM实例
        
        Args:
            purpose: 用途标识
            
        Returns:
            LLM实例，如果未配置返回None
        """
        # 如果已有实例，直接返回
        if purpose in self._llm_instances:
            return self._llm_instances[purpose]
        
        # 查找配置
        llm_config = None
        if purpose in self._custom_configs:
            llm_config = self._custom_configs[purpose].copy()
        elif purpose in self.DEFAULT_CONFIGS:
            llm_config = self.DEFAULT_CONFIGS[purpose].copy()
            if "temperature" not in llm_config:
                llm_config["temperature"] = 0.7
        
        if llm_config is None:
            logger.warning(f"No configuration found for purpose '{purpose}'")
            return None
        
        # 确定使用的 API Key 和 Base URL
        # 优先级：配置中指定的 > 默认配置中的 > 主配置
        api_key = llm_config.get("api_key") or self.default_api_key
        base_url = llm_config.get("base_url") or self.default_base_url
        
        # 创建新实例
        try:
            llm = LLM(
                model=llm_config["model"],
                api_key=api_key,
                base_url=base_url
            )
            llm.temperature = llm_config.get("temperature", 0.7)
            self._llm_instances[purpose] = llm
            return llm
        except Exception as e:
            logger.error(f"Failed to create LLM for purpose '{purpose}': {e}")
            return None
    
    def get_specialized_llms(self, purposes: list[str] = None) -> Dict[str, LLM]:
        """
        批量获取多个专用LLM实例
        
        Args:
            purposes: 用途列表，如果为None则返回所有已配置的
            
        Returns:
            用途到LLM实例的字典
        """
        if purposes is None:
            # 获取所有已配置的
            purposes = list(set(
                list(self._custom_configs.keys()) + 
                list(self.DEFAULT_CONFIGS.keys())
            ))
        
        result = {}
        for purpose in purposes:
            llm = self.get_llm(purpose)
            if llm:
                result[purpose] = llm
        
        return result
    
    def list_available_purposes(self) -> list[tuple[str, str]]:
        """
        列出所有可用的用途及其描述
        
        Returns:
            (用途, 描述) 的列表
        """
        purposes = []
        
        # 自定义配置
        for purpose, llm_config in self._custom_configs.items():
            model = llm_config['model']
            base_url = llm_config.get('base_url') or self.default_base_url
            purposes.append((purpose, f"Custom: {model} @ {base_url}"))
        
        # 默认配置
        for purpose, llm_config in self.DEFAULT_CONFIGS.items():
            if purpose not in self._custom_configs:
                model = llm_config['model']
                base_url = llm_config.get('base_url') or self.default_base_url
                desc = llm_config["description"]
                purposes.append((purpose, f"{desc} ({model} @ {base_url})"))
        
        return purposes


# 全局单例（可选）
_global_manager: Optional[LLMManager] = None


def get_global_manager() -> Optional[LLMManager]:
    """获取全局LLM管理器实例"""
    return _global_manager


def init_global_manager(api_key: str, base_url: str = "https://openrouter.ai/api/v1") -> LLMManager:
    """
    初始化全局LLM管理器
    
    Args:
        api_key: API密钥
        base_url: API基础URL
        
    Returns:
        LLM管理器实例
    """
    global _global_manager
    _global_manager = LLMManager(api_key, base_url)
    return _global_manager


if __name__ == '__main__':
    import os
    
    # 使用示例 - 需要设置环境变量 OPENROUTER_API_KEY
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("请设置环境变量 OPENROUTER_API_KEY")
        exit(1)
    
    manager = LLMManager(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    # 自定义配置（可以指定独立的 base_url）
    manager.configure(
        "thinking", 
        "deepseek/deepseek-reasoner", 
        temperature=0.3,
        base_url="https://api.deepseek.com/v1"  # 可选：使用专门的 base_url
    )
    manager.configure(
        "coding", 
        "anthropic/claude-3.5-sonnet", 
        temperature=0.5
        # 不指定 base_url，使用默认值
    )
    
    # 获取专用LLM
    thinking_llm = manager.get_llm("thinking")
    coding_llm = manager.get_llm("coding")
    
    # 批量获取
    specialized_llms = manager.get_specialized_llms(["thinking", "coding"])
    
    print("Available purposes:")
    for purpose, desc in manager.list_available_purposes():
        print(f"  - {purpose}: {desc}")

