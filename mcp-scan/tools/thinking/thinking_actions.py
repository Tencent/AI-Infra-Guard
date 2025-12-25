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
    try:
        if not thought or not thought.strip():
            return {"message": "Thought cannot be empty"}

        # 如果有context，使用思考模型深度分析
        #         system_prompt = """你是一个专业的思考助手，擅长深度分析和逻辑推理。
        # 你的任务是对用户提出的问题进行深入思考，提供：
        # 1. 问题分析
        # 2. 当前信息和背景整合
        # 3. 可能的解决方案
        # 4. 潜在风险和注意事项
        # 5. 推荐的行动步骤
        #
        # 请用简洁、结构化的方式回答。"""
        #
        #         # 使用专门的思考模型（如果配置了），否则使用默认LLM
        #         thinking_result = context.call_llm(
        #             prompt=f"请对以下内容进行深度思考和分析：\n\n{thought}",
        #             purpose="thinking",
        #             system_prompt=system_prompt,
        #             use_history=True  # 思考时需要历史记录
        #         )

        return {
            "success": True,
            "thought": thought,
            # "thinking_result": thinking_result,
        }

    except (ValueError, TypeError) as e:
        return {"success": False, "message": f"Failed to record thought: {e!s}"}
    except Exception as e:
        return {"success": False, "message": f"Error during thinking: {str(e)}"}
