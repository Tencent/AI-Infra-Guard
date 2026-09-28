"""Agent environments for testing prompt-injection attacks.

An agent wraps a :class:`~pikit.targets.Target` and exposes a ``run()`` that
returns a human-readable :class:`Trace`. Three kinds ship:

* ``chat`` — a plain assistant (no tools); direct injection via the user
  message.
* ``tool`` — a general tool-calling agent; indirect injection via a
  compromised tool's return value (the ``taint`` map).
* scenario agents — ``email`` / ``rag`` / ``browser`` — preconfigured with a
  realistic toolset and an observable *sink*.

Like the rest of pikit, agents register under short keys; use
``get_agent(key)`` to fetch the class, then construct it.
"""

from __future__ import annotations

from ..registry import Registry
from .base import Agent, Trace, TraceStep
from .hooks import DefenseHooks
from .adapters import AgentCallable, AgentRunResult, CallableAgentAdapter
from .tools import Tool, tool
from .system_prompt import build_system_prompt
from .builtin_tools import (
    all_tools, get_tool, get_tools, tools_by_category,
    data_source_tools, sink_tools, tool_names, categories,
    BROWSER_TOOLS, EMAIL_TOOLS, CODING_TOOLS, RAG_TOOLS,
    IM_TOOLS, CALENDAR_TOOLS, FINANCE_TOOLS, TRAVEL_TOOLS,
    SOCIAL_TOOLS, FILE_MANAGER_TOOLS,
)

registry: Registry[Agent] = Registry("agent")
register = registry.register
get_agent = registry.get
list = registry.list  # noqa: A001 - mirror dict-like API on purpose

# Importing the modules triggers their @register decorators.
from . import chat_agent, tool_agent  # noqa: E402,F401
from . import scenarios  # noqa: E402,F401

__all__ = [
    "Agent",
    "Trace",
    "TraceStep",
    "DefenseHooks",
    "AgentCallable",
    "AgentRunResult",
    "CallableAgentAdapter",
    "Tool",
    "tool",
    "build_system_prompt",
    # Tool pool
    "all_tools", "get_tool", "get_tools", "tools_by_category",
    "data_source_tools", "sink_tools", "tool_names", "categories",
    "BROWSER_TOOLS", "EMAIL_TOOLS", "CODING_TOOLS", "RAG_TOOLS",
    "IM_TOOLS", "CALENDAR_TOOLS", "FINANCE_TOOLS", "TRAVEL_TOOLS",
    "SOCIAL_TOOLS", "FILE_MANAGER_TOOLS",
    "registry",
    "register",
    "get_agent",
    "list",
]
