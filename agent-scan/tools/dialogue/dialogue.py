from tools.registry import register_tool
from core.agent_adapter.adapter import AIProviderClient, ProviderTestResult
from utils.tool_context import ToolContext


@register_tool
def dialogue(prompt: str = None, context: ToolContext = None) -> ProviderTestResult:
    return context.call_provider(prompt)
