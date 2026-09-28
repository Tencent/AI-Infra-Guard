"""Framework adapters for running external agents through pikit.

Adapters are optional integrations: install the matching extra only when a
framework is needed.  The core package remains dependency-free.
"""

from ..agent.adapters import AgentCallable, AgentRunResult, CallableAgentAdapter
from .recorder import TraceRecorder
from .taint import TaintRouter, ToolTaintRule
from .runtime_cli import HermesCLIAdapter, OpenClawCLIAdapter, RuntimeCLIAdapter
from .runtime_fixtures import (
    CHANNEL_FIXTURES, FIXTURES, NATIVE_CHANNEL_FIXTURES, RuntimeFixture,
    fixture_for, mapping_kind,
)
from .harness import AgentHarness, get_harness, list_harnesses, register_harness
# Import built-in adapters for registration. Optional framework imports stay
# lazy inside adapter methods, so this does not add runtime dependencies.
from . import langchain, openai_agents, pydantic_ai, runtime_cli  # noqa: F401

__all__ = [
    "AgentCallable",
    "AgentRunResult",
    "CallableAgentAdapter",
    "TraceRecorder",
    "TaintRouter",
    "ToolTaintRule",
    "RuntimeCLIAdapter",
    "OpenClawCLIAdapter",
    "HermesCLIAdapter",
    "RuntimeFixture",
    "FIXTURES",
    "CHANNEL_FIXTURES",
    "fixture_for",
    "mapping_kind",
    "NATIVE_CHANNEL_FIXTURES",
    "AgentHarness",
    "get_harness",
    "list_harnesses",
    "register_harness",
]
