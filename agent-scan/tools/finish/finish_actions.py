from typing import Any

from tools.registry import register_tool
from utils.loging import logger


@register_tool(sandbox_execution=False)
def finish(
        content: str,
) -> dict[str, Any]:
    """结束当前任务。
    
    参数:
    content: 简要说明完成了哪些工作内容。BaseAgent 将以此为基础，结合对话历史生成最终的格式化报告。
    """
    logger.info(f"Finish called with brief: {content}")
    return {"success": True, "message": "Task completion signaled."}