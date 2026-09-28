"""OpenAI Agents SDK integration for pikit experiments.

Install with ``pip install 'pikit[openai-agents]'``. The adapter clones an
SDK ``Agent`` with wrapped function tools, routes selected tool results through
``TaintRouter``, and converts the SDK run items into a pikit ``Trace``.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Iterable, Optional, Set

from ..agent.base import Trace
from ..agent.hooks import DefenseHooks
from .recorder import TraceRecorder
from .taint import TaintRouter
from .harness import register_harness


@register_harness("openai_agents")
class OpenAIAgentsAdapter:
    """Run an OpenAI Agents SDK agent with taintable function tools.

    Parameters
    ----------
    agent:
        An :class:`agents.Agent` instance. The adapter clones its public
        configuration for each run and replaces only configured function
        tools, so the caller's agent remains unchanged.
    taint_router:
        Conditional rules selecting tainted tool responses.
    sink_tools:
        Function-tool names considered externally observable actions.
    defenses:
        User/system/tool-result defenses applied at the matching boundary.

    Notes
    -----
    This first integration intentionally supports SDK ``FunctionTool``
    instances. Hosted tools, MCP tools, and handoffs are preserved on the
    cloned agent but are not intercepted as taint points.
    """

    name = "openai_agents"

    def __init__(
        self,
        agent: Any,
        *,
        taint_router: Optional[TaintRouter] = None,
        sink_tools: Optional[Iterable[str]] = None,
        defenses: Optional[DefenseHooks] = None,
    ) -> None:
        self.agent = agent
        self.taint_router = taint_router or TaintRouter()
        self.sink_tools: Set[str] = set(sink_tools or [])
        self.hooks = defenses or DefenseHooks()

    def _wrapped_agent(self, recorder: TraceRecorder) -> Any:
        try:
            from agents import Agent
            from agents.tool import FunctionTool
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise ImportError(
                "OpenAI Agents SDK support requires "
                "`pip install pikit[openai-agents]`"
            ) from exc

        tools = []
        for original in self.agent.tools:
            if not isinstance(original, FunctionTool):
                tools.append(original)
                continue

            async def invoke(context: Any, input_json: str, _tool=original) -> Any:
                try:
                    args = json.loads(input_json or "{}")
                except (TypeError, json.JSONDecodeError):
                    args = {}
                recorder.tool_call(
                    _tool.name,
                    args,
                    is_sink=_tool.name in self.sink_tools,
                )
                tainted = self.taint_router.resolve(_tool.name, args)
                raw = (
                    tainted
                    if tainted is not None
                    else await _tool.on_invoke_tool(context, input_json)
                )
                content = self.hooks.on_tool_result(str(raw), _tool.name)
                recorder.tool_result(_tool.name, content, tainted=tainted is not None)
                return content

            tools.append(
                FunctionTool(
                    name=original.name,
                    description=original.description,
                    params_json_schema=original.params_json_schema,
                    on_invoke_tool=invoke,
                    strict_json_schema=original.strict_json_schema,
                    is_enabled=original.is_enabled,
                    tool_input_guardrails=original.tool_input_guardrails,
                    tool_output_guardrails=original.tool_output_guardrails,
                    needs_approval=original.needs_approval,
                    timeout_seconds=original.timeout_seconds,
                    timeout_behavior=original.timeout_behavior,
                    timeout_error_function=original.timeout_error_function,
                    defer_loading=original.defer_loading,
                    custom_data_extractor=original.custom_data_extractor,
                    allowed_callers=original.allowed_callers,
                    output_json_schema=original.output_json_schema,
                )
            )

        # Agent dataclasses expose configuration as public attributes.
        # Preserve every relevant public execution setting while replacing
        # only standard function tools. Apply a static system defense before
        # cloning; dynamic instruction functions stay untouched.
        instructions = self.agent.instructions
        if isinstance(instructions, str):
            instructions = self.hooks.on_system(instructions)
        return Agent(
            name=self.agent.name,
            handoff_description=self.agent.handoff_description,
            tools=tools,
            mcp_servers=list(self.agent.mcp_servers),
            mcp_config=self.agent.mcp_config,
            instructions=instructions,
            prompt=self.agent.prompt,
            handoffs=list(self.agent.handoffs),
            model=self.agent.model,
            model_settings=self.agent.model_settings,
            input_guardrails=list(self.agent.input_guardrails),
            output_guardrails=list(self.agent.output_guardrails),
            output_type=self.agent.output_type,
            hooks=self.agent.hooks,
            tool_use_behavior=self.agent.tool_use_behavior,
            reset_tool_choice=self.agent.reset_tool_choice,
        )

    async def arun(
        self,
        user_message: str,
        *,
        max_turns: int = 10,
        run_config: Any = None,
        **kwargs: Any,
    ) -> Trace:
        """Asynchronously run the wrapped SDK agent and return a pikit trace."""
        try:
            from agents import Runner
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise ImportError(
                "OpenAI Agents SDK support requires "
                "`pip install pikit[openai-agents]`"
            ) from exc

        recorder = TraceRecorder()
        message = self.hooks.on_user(user_message)
        recorder.system(
            self.hooks.on_system(self.agent.instructions)
            if isinstance(self.agent.instructions, str)
            else None
        )
        recorder.user(message)
        result = await Runner.run(
            self._wrapped_agent(recorder),
            message,
            max_turns=max_turns,
            run_config=run_config,
            **kwargs,
        )
        return recorder.finish(result.final_output)

    def run(self, user_message: str, **kwargs: Any) -> Trace:
        """Synchronously run the adapter outside an active event loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(user_message, **kwargs))
        raise RuntimeError(
            "OpenAIAgentsAdapter.run() cannot be called from an active event "
            "loop; use `await adapter.arun(...)` instead."
        )


__all__ = ["OpenAIAgentsAdapter"]
