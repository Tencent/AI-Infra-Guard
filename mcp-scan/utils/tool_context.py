"""
工具执行上下文 - 提供工具运行所需的环境信息
"""
from typing import List, Dict, Any, Optional
from utils.llm import LLM


class ToolContext:
    """工具执行上下文，包含历史记录、LLM实例等信息"""

    def __init__(
            self,
            llm: LLM,
            history: List[Dict[str, str]],
            agent_name: str = "Agent",
            iteration: int = 0,
            specialized_llms: Optional[Dict[str, LLM]] = None,
            repo_dir: str = ""
    ):
        """
        初始化工具上下文
        
        Args:
            llm: 主要使用的LLM实例
            history: 对话历史记录
            agent_name: Agent名称
            iteration: 当前迭代次数
            specialized_llms: 专用LLM字典，key为用途(如"thinking", "coding")
        """
        self.llm = llm
        self.history = history
        self.agent_name = agent_name
        self.iteration = iteration
        self.specialized_llms = specialized_llms or {}
        self.repo_dir = repo_dir

    def get_llm(self, purpose: str = "default") -> LLM:
        """
        根据用途获取合适的LLM
        
        Args:
            purpose: LLM用途，如 "thinking", "coding", "default"
            
        Returns:
            LLM实例
        """
        if purpose in self.specialized_llms:
            return self.specialized_llms[purpose]
        return self.llm

    def get_recent_history(self, n: int = 5) -> List[Dict[str, str]]:
        """
        获取最近的n条历史记录
        
        Args:
            n: 历史记录条数
            
        Returns:
            历史记录列表
        """
        return self.history[-n:] if len(self.history) > n else self.history

    def call_llm(
            self,
            prompt: str,
            purpose: str = "default",
            system_prompt: Optional[str] = None,
            use_history: bool = False
    ) -> str:
        """
        调用LLM获取响应
        
        Args:
            prompt: 用户提示
            purpose: LLM用途
            system_prompt: 系统提示（可选）
            use_history: 是否使用历史记录
            
        Returns:
            LLM响应内容
        """
        llm = self.get_llm(purpose)

        messages = []

        # 添加系统提示
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 添加历史记录（如果需要）
        if use_history:
            messages.extend(self.history[1:])

        # 添加当前提示
        messages.append({"role": "user", "content": prompt})

        return llm.chat(messages)

    def call_llm_messages(
            self,
            messages,
            purpose: str = "default",
    ) -> str:
        llm = self.get_llm(purpose)
        return llm.chat(messages)
