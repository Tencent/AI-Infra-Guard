import time
import asyncio
from openai import OpenAI, AsyncOpenAI
from deepeval.models.base_model import DeepEvalBaseLLM


class OpenaiAlikeModel(DeepEvalBaseLLM):
    """自定义模型，用于支持OpenAI API Alike Model"""
    max_trial = 3
    base_wait_seconds = 0.5

    def __init__(self, model_name: str, base_url: str, api_key: str, max_concurrent: int):
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.async_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    
    def load_model(self):
        return self.client
    
    def test_model_connection(self):
        """
        测试模型是否连通
        
        返回:
            bool: True 表示连通，False 表示连接失败
            str: 返回的响应内容或错误信息
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hi"}],
                max_completion_tokens=10
            )
            return True, response.choices[0].message.content
        except Exception as e:
            return False, str(e)

    def generate(self, prompt: str, system_message: str = None) -> str:
        for i in range(self.max_trial):
            try:
                messages = []
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                messages.append({"role": "user", "content": prompt})
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    reasoning_effort="low",
                    max_completion_tokens=2048,
                    frequency_penalty=1.0
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
    
    async def a_generate(self, prompt: str, system_message: str = None) -> str:
        async with self.semaphore:
            for i in range(self.max_trial):
                try:
                    messages = []
                    if system_message:
                        messages.append({"role": "system", "content": system_message})
                    messages.append({"role": "user", "content": prompt})
                    
                    response = await self.async_client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        reasoning_effort="low",
                        max_completion_tokens=2048,
                        frequency_penalty=1.0
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


def create_model(model_name: str, base_url: str, api_key: str, max_concurrent: int) -> OpenaiAlikeModel:
    """创建模型实例"""
    return OpenaiAlikeModel(
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
        max_concurrent=max_concurrent
    )