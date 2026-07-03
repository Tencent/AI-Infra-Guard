from typing import Any

from skill_scan.utils.tool_context import ToolContext
from skill_scan.tools.registry import register_tool
from skill_scan.utils.loging import logger


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

        # If a context is available, use a reasoning model for deep analysis
        #         system_prompt = """You are a professional thinking assistant skilled in deep analysis and logical reasoning.
        # Your task is to think deeply about the user's question and provide:
        # 1. Problem analysis
        # 2. Integration of current information and background
        # 3. Possible solutions
        # 4. Potential risks and caveats
        # 5. Recommended action steps
        #
        # Please answer in a concise, structured way."""
        #
        #         # Use a dedicated reasoning model (if configured), otherwise fall back to the default LLM
        #         thinking_result = context.call_llm(
        #             prompt=f"Please think deeply about and analyze the following:\n\n{thought}",
        #             purpose="thinking",
        #             system_prompt=system_prompt,
        #             use_history=True  # History is needed for thinking
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
