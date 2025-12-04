from typing import Any

from utils.tool_context import ToolContext
from tools.registry import register_tool
from utils.loging import logger


@register_tool(sandbox_execution=False)
def think(thought: str, context: ToolContext = None) -> dict[str, Any]:
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
    if not context:
        return {"success": False, "message": "Tool context required for thinking."}

    logger.info(f"Agent is thinking about: {thought[:100]}...")

    try:
        if not thought or not thought.strip():
            return {"success": False, "message": "Thought cannot be empty"}

        # Enhanced System Prompt for Deep Reasoning
        # Inspired by Chain-of-Thought and Tree-of-Thoughts prompting
        system_prompt = """You are the **Reasoning Engine** for an autonomous software agent.
Your goal is to provide deep, structured analysis to help the agent solve complex problems.

You are NOT the one executing the code. You are the BRAIN.
The agent is currently stuck or needs a plan.

Analyze the provided situation using the following framework:

1.  **Deconstruction**: Break down the problem into its fundamental components. What are the knowns? What are the unknowns?
2.  **Hypothesis Generation**: Formulate 2-3 possible approaches or explanations.
3.  **Critical Evaluation**: For each hypothesis, list pros, cons, and risks.
4.  **Selection & Planning**: Select the best approach. Create a concrete, step-by-step plan for the agent to follow.
    *   Specify which tools to use for each step.
    *   Identify what to verify after each step.

**Output Format:**
Please provide your response in a clear, structured Markdown format.
Start with a brief "High-Level Summary" and then go into the details.
End with a "Recommended Next Action" section that gives the agent its immediate next command.
"""

        # We include recent history to give the thinker context on what has happened so far
        # This is crucial for "I'm stuck" scenarios
        recent_history = context.get_recent_history(n=10)
        history_text = ""
        for msg in recent_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user" or role == "model" or role == "assistant":
                history_text += f"{role.upper()}: {content[:500]}...\n" # Truncate to save tokens

        prompt = f"""
## Context (Recent Conversation History)
{history_text}

## Current Dilemma / Thought Topic
{thought}

## Task
Please analyze this situation deeply. Why is this happening? What should be done next?
"""

        # Use specialized 'thinking' model if available, otherwise default
        thinking_result = context.call_llm(
            prompt=prompt,
            purpose="thinking",
            system_prompt=system_prompt,
            use_history=False # We manually injected curated history above
        )

        logger.info("Thinking complete.")

        return {
            "success": True,
            "thought_input": thought,
            "analysis": thinking_result,
            "guidance": "Review the analysis above and proceed with the Recommended Next Action."
        }

    except Exception as e:
        logger.error(f"Error during thinking: {e}", exc_info=True)
        return {"success": False, "message": f"Error during thinking: {str(e)}"}
