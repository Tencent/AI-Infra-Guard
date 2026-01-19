from tools.registry import register_tool
from utils.aig_logger import mcpLogger
from .adapter import default_client


@register_tool
def connectivity(config_file: str) -> bool:
    default_prompt = "Only return 1"
    providers = default_client.load_config_from_file(config_file)

    result = default_client.call_provider(providers[0], default_prompt)
    mcpLogger.result_update(content=result.model_dump())

    return result.success