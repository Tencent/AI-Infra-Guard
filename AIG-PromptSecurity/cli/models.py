from langchain_openai import ChatOpenAI
from deepeval.models.base_model import DeepEvalBaseLLM
from pydantic import SecretStr


class OpenaiAlikeModel(DeepEvalBaseLLM):
    """自定义模型，用于支持OpenAI API Alike Model"""
    
    def __init__(self, model):
        self.model = model
    
    def load_model(self):
        return self.model
    
    def generate(self, prompt: str) -> str:
        chat_model = self.load_model()
        if not isinstance(chat_model.invoke(prompt).content, str):
            raise ValueError("The response is not a string")
        return chat_model.invoke(prompt).content
    
    async def a_generate(self, prompt: str) -> str:
        chat_model = self.load_model()
        res = await chat_model.ainvoke(prompt)
        return res.content
    
    def get_model_name(self):
        return self.model.model_name


def create_model(model_name: str, base_url: str, api_key: str) -> OpenaiAlikeModel:
    """创建模型实例"""
    openrouter = ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=SecretStr(api_key)
    )
    return OpenaiAlikeModel(openrouter)
