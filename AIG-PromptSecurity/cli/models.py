import time
import asyncio
from langchain_openai import ChatOpenAI
from deepeval.models.base_model import DeepEvalBaseLLM
from pydantic import SecretStr


class OpenaiAlikeModel(DeepEvalBaseLLM):
    """自定义模型，用于支持OpenAI API Alike Model"""
    max_trial = 3
    base_wait_seconds = 0.5

    def __init__(self, model: ChatOpenAI, max_concurrent):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.model = model
    
    def load_model(self):
        return self.model
    
    def test_model_connection(self):
        """
        测试 ChatOpenAI 模型是否连通。
        
        参数:
            model_name (str): 模型名称，默认 "gpt-4"
            temperature (float): 采样温度，默认 0
        
        返回:
            bool: True 表示连通，False 表示连接失败
            str: 返回的响应内容或错误信息
        """
        chat_model = self.load_model()
        try:
            response = chat_model.invoke("Hi").content
            return True, response
        except Exception as e:
            return False, e

    def generate(self, prompt: str) -> str:
        for i in range(self.max_trial):
            try:
                chat_model = self.load_model()
                res = chat_model.invoke(prompt).content
                if not isinstance(res, str):
                    raise ValueError("The response is not a string")
                return res
            except Exception as e:
                wait_time = self.base_wait_seconds * (2 ** i)
                time.sleep(wait_time)
        return ""
    
    async def a_generate(self, prompt: str) -> str:
        async with self.semaphore:
            for i in range(self.max_trial):
                try:
                    chat_model = self.load_model()
                    res = await chat_model.ainvoke(prompt)
                    if not isinstance(res.content, str):
                        raise ValueError("The response is not a string")
                    return res.content
                except Exception as e:
                    wait_time = self.base_wait_seconds * (2 ** i)
                    await asyncio.sleep(wait_time)
            return ""
    
    def get_model_name(self):
        return self.model.model_name


def create_model(model_name: str, base_url: str, api_key: str, max_concurrent: int) -> OpenaiAlikeModel:
    """创建模型实例"""
    openrouter = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=SecretStr(api_key),
        max_tokens=1024,
        frequency_penalty=1.0
    )
    return OpenaiAlikeModel(openrouter, max_concurrent)