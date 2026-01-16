from tools.registry import register_tool
from .adapter import default_client, ProviderTestResult


@register_tool
def dialogue(config_file: str, prompt: str = None) -> ProviderTestResult:
    providers = default_client.load_config_from_file(config_file)

    result = default_client.call_provider(providers[0], prompt)
    return result