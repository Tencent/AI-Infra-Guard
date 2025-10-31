import time
import asyncio
from openai import OpenAI, AsyncOpenAI
from .base import BaseLLM

class OpenaiAlikeModel(BaseLLM):
    """自定义模型，用于支持OpenAI API Alike Model"""
    max_trial = 3 
    base_wait_seconds = 0.5

    def __init__(self, model_name: str, base_url: str, api_key: str, max_concurrent: int, *args, **kwargs):
        super().__init__(model_name, base_url, api_key, max_concurrent, *args, **kwargs)
        self.load_model()
    
    def load_model(self):
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        self.async_client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        self.default_params = {
            "reasoning_effort": "low",
            "frequency_penalty": 1.0,
            "max_completion_tokens": 2048
        }
        return self.client
    
    def test_model_connection(self):
        """
        测试模型是否连通
        
        返回:
            bool: True 表示连通，False 表示连接失败
            str: 返回的响应内容或错误信息
        """
        current_params = self.default_params.copy()
        param_keys = list(current_params.keys())
        for i in range(len(param_keys) + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": "only return 1"}],
                    **current_params
                )
                # 如果成功，返回成功的信息和使用的参数
                self.default_params = current_params.copy()
                return True, response.choices[0].message.content
            except Exception as e:
                last_error = str(e)
                # 如果还有参数可以移除，移除下一个参数
                if i < len(param_keys):
                    param_to_remove = param_keys[i]
                    current_params.pop(param_to_remove, None)
                # 否则继续循环（最后一次尝试无参数）

        # 所有尝试都失败
        return False, last_error

    def generate(self, prompt: str = None, messages: list = None) -> str:
        for i in range(self.max_trial):
            try:
                if prompt:
                    _messages = [{"role": "user", "content": prompt}]
                elif messages:
                    _messages = messages
                else:
                    raise ValueError("prompt and messages cannot both be empty")
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=_messages,
                    **self.default_params
                )
                content = response.choices[0].message.content
                if not isinstance(content, str):
                    raise ValueError("The response is not a string")
                elif not content:
                    raise ValueError("The response is empty")
                return content
            except Exception as e:
                wait_time = self.base_wait_seconds * (2 ** i)
                time.sleep(wait_time)
        return ""
    
    async def a_generate(self, prompt: str = None, messages: list = None) -> str:
        async with self.semaphore:
            for i in range(self.max_trial):
                try:
                    if prompt:
                        _messages = [{"role": "user", "content": prompt}]
                    elif messages:
                        _messages = messages
                    else:
                        raise ValueError("prompt and messages cannot both be empty")
                    
                    response = await self.async_client.chat.completions.create(
                        model=self.model_name,
                        messages=_messages,
                        **self.default_params
                    )
                    content = response.choices[0].message.content
                    if not isinstance(content, str):
                        raise ValueError("The response is not a string")
                    elif not content:
                        raise ValueError("The response is empty")
                    return content
                except Exception as e:
                    wait_time = self.base_wait_seconds * (2 ** i)
                    await asyncio.sleep(wait_time)
            return ""
    
    def get_model_name(self):
        return self.model_name