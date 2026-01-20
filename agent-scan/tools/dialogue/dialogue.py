from tools.registry import register_tool
from core.agent_adapter.adapter import AIProviderClient, ProviderTestResult
from utils.tool_context import ToolContext
from utils.loging import logger

@register_tool
def dialogue(prompt: str = None, context: ToolContext = None) -> ProviderTestResult:
    result: ProviderTestResult = context.call_provider(prompt)
    logger.info(f"Dialogue result: {result}")
    return result.provider_response.output
