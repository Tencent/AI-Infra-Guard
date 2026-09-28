"""A no-tools chat agent — the simplest target under test."""

from __future__ import annotations

from typing import Optional

from ..targets import Target
from . import register
from .base import Agent, Trace, TraceStep
from .hooks import DefenseHooks


@register("chat")
class ChatAgent(Agent):
    """A plain chat assistant with no tools.

    Wraps :meth:`Target.query`; direct injection arrives as the user
    message. The ``system`` and ``user`` defense hooks apply (there are no
    tool results to defend).
    """

    def run(self, user_message: str, **kwargs) -> Trace:
        trace = Trace()
        system = self.hooks.on_system(self.system)
        if system:
            trace.add(TraceStep("system", text=system))

        message = self.hooks.on_user(user_message)
        trace.add(TraceStep("user", text=message))

        reply = self.target.query(message, system=system, **kwargs)
        trace.add(TraceStep("model", text=reply))
        trace.final_text = reply
        return trace
