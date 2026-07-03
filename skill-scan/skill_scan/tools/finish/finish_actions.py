from typing import Any

from skill_scan.tools.registry import register_tool
from skill_scan.utils.loging import logger


@register_tool(sandbox_execution=False)
def finish(
        content: str,
) -> dict[str, Any]:
    """End the current task.

    Args:
        content: A brief description of the work completed. BaseAgent will use this,
                  together with the conversation history, to generate the final formatted report.
    """
    logger.info(f"Finish called with brief: {content}")
    return {"success": True, "message": "Task completion signaled."}