from typing import Any

from tools.registry import register_tool
from utils.loging import logger


@register_tool(sandbox_execution=False)
def finish(
        content: str,
) -> dict[str, Any]:
    logger.info(f"Finish: {content}")
    return {"success": True, "message": content}
