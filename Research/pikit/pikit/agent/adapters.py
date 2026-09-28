"""Adapters for exercising externally implemented agents with pikit.

The built-in scenarios are controlled testbeds. An adapter lets a researcher
bring an existing agent runner while retaining pikit's ``Trace`` and judge
interfaces.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Union

from .base import Agent, Trace, TraceStep
from .hooks import DefenseHooks

AgentRunResult = Union[str, Trace]
AgentCallable = Callable[..., AgentRunResult]


class CallableAgentAdapter(Agent):
    """Wrap a user-supplied agent callable as a pikit agent.

    The callable receives the hardened user message. It may return either a
    final text string or a fully populated :class:`Trace`. Optional keyword
    arguments expose the adapter context to framework integrations:
    ``system``, ``taint``, and ``defenses``.

    Returning a ``Trace`` is recommended whenever the external framework can
    capture tool calls. Returning text still provides a useful minimal
    adapter for direct-injection testing.
    """

    name = "callable"

    def __init__(
        self,
        runner: AgentCallable,
        *,
        system: Optional[str] = None,
        taint: Optional[Dict[str, str]] = None,
        defenses: Optional[DefenseHooks] = None,
    ) -> None:
        # The external runner owns its model client, so there is no native
        # pikit Target instance to store here.
        super().__init__(target=None, system=system, defenses=defenses)  # type: ignore[arg-type]
        self.runner = runner
        self.taint = dict(taint or {})

    def run(self, user_message: str, **kwargs: Any) -> Trace:
        system = self.hooks.on_system(self.system)
        hardened_user = self.hooks.on_user(user_message)
        result = self.runner(
            hardened_user,
            system=system,
            taint=dict(self.taint),
            defenses=self.hooks,
            **kwargs,
        )
        if isinstance(result, Trace):
            return result
        trace = Trace()
        if system:
            trace.add(TraceStep("system", text=system))
        trace.add(TraceStep("user", text=hardened_user))
        trace.add(TraceStep("model", text=str(result)))
        trace.final_text = str(result)
        return trace


__all__ = ["AgentCallable", "AgentRunResult", "CallableAgentAdapter"]
