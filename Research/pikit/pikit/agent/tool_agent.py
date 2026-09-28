"""A general tool-calling agent driven by the function-calling loop."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..targets import Target
from . import register
from .base import Agent, Trace
from .hooks import DefenseHooks
from .loop import run_tool_loop
from .tools import Tool


@register("tool")
class ToolAgent(Agent):
    """An agent that can call a fixed set of tools in a loop.

    Parameters
    ----------
    target, system, defenses:
        See :class:`~pikit.agent.base.Agent`.
    tools:
        The tools exposed to the model.
    taint:
        Map of ``tool_name -> artifact`` marking compromised tools whose
        return value is replaced by the injected artifact (indirect-injection
        delivery point). See :func:`~pikit.agent.loop.run_tool_loop`.
    max_steps:
        Safety cap on loop iterations.
    """

    def __init__(
        self,
        target: Target,
        *,
        tools: Optional[List[Tool]] = None,
        taint: Optional[Dict[str, str]] = None,
        system: Optional[str] = None,
        defenses: Optional[DefenseHooks] = None,
        max_steps: int = 8,
    ) -> None:
        super().__init__(target, system=system, defenses=defenses)
        self.tools = tools or []
        self.taint = taint or {}
        self.max_steps = max_steps

    def run(self, user_message: str, **kwargs) -> Trace:
        return run_tool_loop(
            self.target,
            user_message,
            self.tools,
            system=self.system,
            hooks=self.hooks,
            taint=self.taint,
            max_steps=self.max_steps,
            **kwargs,
        )
