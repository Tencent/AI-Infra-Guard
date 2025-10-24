from cli.model_utils import BaseLLM
from cli.model_utils.openailike import OpenaiAlikeModel

def create_model(model_name: str, base_url: str, api_key: str, max_concurrent: int) -> BaseLLM:
    """创建模型实例"""
    return OpenaiAlikeModel(
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
        max_concurrent=max_concurrent
    )