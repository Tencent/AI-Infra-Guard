"""LangChain integration for pikit tool-result injection experiments.

Install with ``pip install 'pikit[langchain]'``.  The adapter wraps ordinary
LangChain function tools, replaces selected results through :class:`TaintRouter`,
and converts the invocation into a pikit :class:`~pikit.agent.Trace`.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Optional, Set

from ..agent.base import Trace
from ..agent.hooks import DefenseHooks
from .recorder import TraceRecorder
from .taint import TaintRouter
from .harness import register_harness


@register_harness("langchain")
class LangChainAdapter:
    """Run a LangChain Runnable with taintable tools and a pikit trace.

    Parameters
    ----------
    agent:
        An already-built LangChain runnable, normally created via
        ``langchain.create_agent``. Use ``agent_factory`` when tools need
        tracing or taint injection.
        It must accept ``{"messages": [("user", message)]}`` and return a
        state containing a ``messages`` list.
    tools:
        The original LangChain tools exposed to the runnable.
    agent_factory:
        Optional callable receiving wrapped tools and returning a runnable.
        This is the recommended integration form because wrappers are created
        per run and share that run's trace recorder.
    taint_router:
        Optional conditional router for compromised tool results.
    sink_tools:
        Tool names considered externally observable actions.
    system:
        Optional system prompt recorded in the trace.  The adapter does not
        mutate a pre-built agent's prompt; callers should configure that
        prompt when constructing the LangChain agent.
    defenses:
        ``tool_result`` is applied to every wrapped tool result before it is
        returned to LangChain. ``user`` and ``system`` are applied before
        recording/invocation.
    """

    name = "langchain"

    def __init__(
        self,
        agent: Any = None,
        tools: Iterable[Any] = (),
        *,
        agent_factory: Optional[Callable[[list], Any]] = None,
        taint_router: Optional[TaintRouter] = None,
        sink_tools: Optional[Iterable[str]] = None,
        system: Optional[str] = None,
        defenses: Optional[DefenseHooks] = None,
    ) -> None:
        if agent is None and agent_factory is None:
            raise ValueError("provide either an agent or an agent_factory")
        self.agent = agent
        self.agent_factory = agent_factory
        self.tools = list(tools)
        self.taint_router = taint_router or TaintRouter()
        self.sink_tools: Set[str] = set(sink_tools or [])
        self.system = system
        self.hooks = defenses or DefenseHooks()

    def wrapped_tools(self, recorder: TraceRecorder) -> list:
        """Return schema-preserving LangChain wrappers for configured tools."""
        try:
            from langchain_core.tools import StructuredTool
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise ImportError(
                "LangChain support requires `pip install pikit[langchain]`"
            ) from exc

        wrapped = []
        for original in self.tools:
            def invoke_original(
                _tool=original, **kwargs: Any
            ) -> str:
                tool_name = _tool.name
                is_sink = tool_name in self.sink_tools
                recorder.tool_call(tool_name, kwargs, is_sink=is_sink)
                tainted = self.taint_router.resolve(tool_name, kwargs)
                raw = tainted if tainted is not None else _tool.invoke(kwargs)
                content = self.hooks.on_tool_result(str(raw), tool_name)
                recorder.tool_result(
                    tool_name, content, tainted=tainted is not None
                )
                return content

            wrapped.append(
                StructuredTool.from_function(
                    name=original.name,
                    description=original.description,
                    func=invoke_original,
                    args_schema=original.args_schema,
                    return_direct=original.return_direct,
                    handle_tool_error=original.handle_tool_error,
                    handle_validation_error=original.handle_validation_error,
                    response_format=original.response_format,
                )
            )
        return wrapped

    def run(self, user_message: str, **kwargs: Any) -> Trace:
        """Invoke the configured runnable and return a pikit trace.

        ``agent_factory`` is recommended for real agents: it receives
        per-run wrapped tools and returns the runnable. This avoids unsafe
        monkey-patching of framework internals.
        """
        recorder = kwargs.pop("recorder", None) or TraceRecorder()
        system = self.hooks.on_system(self.system)
        message = self.hooks.on_user(user_message)
        recorder.system(system)
        recorder.user(message)

        agent = (
            self.agent_factory(self.wrapped_tools(recorder))
            if self.agent_factory is not None
            else self.agent
        )
        result = agent.invoke({"messages": [("user", message)]}, **kwargs)
        messages = result.get("messages", []) if isinstance(result, dict) else []
        final = self._final_text(messages, result)
        return recorder.finish(final)

    @staticmethod
    def _final_text(messages: Any, result: Any) -> str:
        if messages:
            final = messages[-1]
            content = getattr(final, "content", final)
            if isinstance(content, list):
                return "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in content
                )
            return str(content or "")
        return str(result or "")


__all__ = ["LangChainAdapter"]
