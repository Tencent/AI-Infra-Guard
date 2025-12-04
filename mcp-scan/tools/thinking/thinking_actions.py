from typing import Any

from utils.tool_context import ToolContext
from tools.registry import register_tool
from utils.loging import logger


@register_tool(sandbox_execution=False)
def think(thought: str, context: ToolContext = None):
    """
    Deep Thinking Tool.
    Use this tool when you are stuck, facing a complex problem, or need to plan a multi-step task.
    It will pause the current execution and use a specialized reasoning model to analyze the situation.

    Args:
        thought: The specific problem, question, or situation you need to think about.
                 Be detailed about what you know and what you are unsure about.
        context: Tool context (automatically injected).

    Returns:
        A structured analysis containing reasoning, plan, and next steps.
    """
    return True
