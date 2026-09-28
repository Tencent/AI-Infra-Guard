"""PydanticAI integration for pikit agent-security experiments.

Install with ``pip install 'pikit[pydantic-ai]'``. The adapter uses
PydanticAI's public ``Agent.override(tools=...)`` testing API to substitute
wrapped function tools for a run, then maps the resulting message history to
a pikit trace.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, Optional, Set

from ..agent.base import Trace
from ..agent.hooks import DefenseHooks
from .recorder import TraceRecorder
from .taint import TaintRouter
from .harness import register_harness


@register_harness("pydantic_ai")
class PydanticAIAdapter:
    """Run a PydanticAI ``Agent`` with taintable function tools.

    Parameters
    ----------
    agent:
        A PydanticAI agent.
    tools:
        Original ``pydantic_ai.tools.Tool`` instances to expose for the
        wrapped run. Supplying tools explicitly keeps the integration public
        API only; tools registered via ``@agent.tool`` can be supplied as
        ``Tool(function)`` when constructing the adapter.
    taint_router:
        Rules selecting a tainted result based on tool name and arguments.
    sink_tools:
        Function-tool names that represent external side effects.
    defenses:
        Standard pikit defenses applied at user, system, and tool-result
        boundaries.
    """

    name = "pydantic_ai"

    def __init__(
        self,
        agent: Any,
        tools: Iterable[Any],
        *,
        taint_router: Optional[TaintRouter] = None,
        sink_tools: Optional[Iterable[str]] = None,
        defenses: Optional[DefenseHooks] = None,
    ) -> None:
        self.agent = agent
        self.tools = list(tools)
        self.taint_router = taint_router or TaintRouter()
        self.sink_tools: Set[str] = set(sink_tools or [])
        self.hooks = defenses or DefenseHooks()

    def _wrapped_tools(self, recorder: TraceRecorder) -> list:
        try:
            from pydantic_ai.tools import Tool
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise ImportError(
                "PydanticAI support requires `pip install pikit[pydantic-ai]`"
            ) from exc

        wrapped = []
        for original in self.tools:
            async def invoke(*args: Any, _tool=original, **kwargs: Any) -> str:
                # PydanticAI context tools receive RunContext as their first
                # argument. Preserve it for the original function while only
                # matching user-provided schema arguments.
                call_args = dict(kwargs)
                if _tool.takes_ctx:
                    original_args = args
                else:
                    original_args = args
                    if args:
                        # Tool schemas are normally keyword-based; retain a
                        # readable representation when a custom positional
                        # function is used.
                        call_args["_args"] = list(args)

                recorder.tool_call(
                    _tool.name,
                    call_args,
                    is_sink=_tool.name in self.sink_tools,
                )
                tainted = self.taint_router.resolve(_tool.name, call_args)
                if tainted is None:
                    raw = _tool.function(*original_args, **kwargs)
                    if hasattr(raw, "__await__"):
                        raw = await raw
                else:
                    raw = tainted
                content = self.hooks.on_tool_result(str(raw), _tool.name)
                recorder.tool_result(_tool.name, content, tainted=tainted is not None)
                return content

            # Keep the original JSON schema while replacing its implementation.
            # Reusing FunctionSchema directly would retain the original
            # callable and bypass the wrapper.
            wrapped.append(
                Tool.from_schema(
                    invoke,
                    name=original.name,
                    description=original.description,
                    json_schema=original.function_schema.json_schema,
                    takes_ctx=original.takes_ctx,
                    sequential=original.sequential,
                    args_validator=original.args_validator,
                )
            )
        return wrapped

    async def arun(self, user_message: str, **kwargs: Any) -> Trace:
        """Asynchronously run the adapter and return a structured trace."""
        recorder = TraceRecorder()
        system_prompts = getattr(self.agent, "_system_prompts", ())
        system = "\n".join(system_prompts) if system_prompts else None
        system = self.hooks.on_system(system)
        message = self.hooks.on_user(user_message)
        recorder.system(system)
        recorder.user(message)

        with self.agent.override(tools=self._wrapped_tools(recorder)):
            result = await self.agent.run(message, **kwargs)
        return recorder.finish(result.output)

    def run(self, user_message: str, **kwargs: Any) -> Trace:
        """Synchronously run the adapter outside an active event loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(user_message, **kwargs))
        raise RuntimeError(
            "PydanticAIAdapter.run() cannot be called from an active event "
            "loop; use `await adapter.arun(...)` instead."
        )


__all__ = ["PydanticAIAdapter"]
