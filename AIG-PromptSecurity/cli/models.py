import time
import asyncio
from typing import Optional, Dict, Any
from openai import OpenAI, AsyncOpenAI
from deepeval.models.base_model import DeepEvalBaseLLM
from .http_endpoint_model import HTTPEndpointModel


class OpenaiAlikeModel(DeepEvalBaseLLM):
    """自定义模型，用于支持OpenAI API Alike Model"""
    max_trial = 3
    base_wait_seconds = 0.5

    def __init__(self, model_name: str, base_url: str, api_key: str, max_concurrent: int, request_interval: int = 0):
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.max_concurrent = max_concurrent
        self.request_interval = request_interval  # 请求间隔（毫秒）
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
        # 请求前的频率控制
        if self.request_interval > 0:
            time.sleep(self.request_interval / 1000.0)  # 转换毫秒到秒
            
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
                
                # 请求后的频率控制
                if self.request_interval > 0:
                    print(f"[DEBUG] 同步方法等待请求间隔: {self.request_interval}ms")
                    time.sleep(self.request_interval / 1000.0)  # 转换毫秒到秒
                    print(f"[DEBUG] 同步方法请求间隔等待完成")
                
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
        # 请求前的频率控制
        if self.request_interval > 0:
            await asyncio.sleep(self.request_interval / 1000.0)  # 转换毫秒到秒
            
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
                    
                    # 请求后的频率控制
                    if self.request_interval > 0:
                        print(f"[DEBUG] 异步方法等待请求间隔: {self.request_interval}ms")
                        await asyncio.sleep(self.request_interval / 1000.0)  # 转换毫秒到秒
                        print(f"[DEBUG] 异步方法请求间隔等待完成")
                    
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


def create_model(model_name: str, base_url: str, api_key: str, max_concurrent: int, 
                model_type: str = "openai", **kwargs) -> DeepEvalBaseLLM:
    """创建模型实例
    
    Args:
        model_name: 模型名称
        base_url: 基础URL（对于openai类型）或HTTP端点（对于http_endpoint类型）
        api_key: API密钥（对于openai类型，http_endpoint类型可以为空）
        max_concurrent: 最大并发数
        model_type: 模型类型，"openai" 或 "http_endpoint"
        **kwargs: 其他参数，包括request_interval
    """
    request_interval = kwargs.get("request_interval", 0)  # 默认无间隔
    print(f"[DEBUG] create_model 调用: model_name={model_name}, model_type={model_type}, request_interval={request_interval}")
    
    if model_type == "http_endpoint":
        return HTTPEndpointModel(
            model_name=model_name,
            http_endpoint=base_url,  # 对于HTTP端点，base_url实际是endpoint
            http_method=kwargs.get("http_method", "POST"),
            http_headers=kwargs.get("http_headers", {}),
            http_request_body=kwargs.get("http_request_body"),
            http_response_transform=kwargs.get("http_response_transform"),
            max_concurrent=max_concurrent,
            request_interval=request_interval
        )
    else:
        # 默认为OpenAI兼容模型
        return OpenaiAlikeModel(
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            max_concurrent=max_concurrent,
            request_interval=request_interval
        )