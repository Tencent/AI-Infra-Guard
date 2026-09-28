"""Provider-agnostic data structures for tool-calling chat.

These normalize the differences between backends (OpenAI vs Anthropic) so
the agent loop never branches on which provider it is talking to. They are
plain, zero-dependency dataclasses importable by both ``targets`` and
``agent``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ToolCall:
    """A model's request to invoke a tool."""

    id: str  #: provider call id; synthesized (e.g. "mock-1") for the mock
    name: str  #: the tool the model picked
    args: Dict[str, Any] = field(default_factory=dict)  #: parsed JSON arguments


@dataclass(frozen=True)
class ToolResult:
    """The result of running a tool, fed back to the model."""

    id: str  #: must match the ToolCall.id it answers
    name: str
    content: str  #: stringified tool output


@dataclass(frozen=True)
class ChatResponse:
    """A normalized single assistant turn."""

    text: str = ""  #: assistant free text ("" if it only called tools)
    tool_calls: List[ToolCall] = field(default_factory=list)
    stop_reason: Optional[str] = None  #: "tool_use" | "end" | provider raw
    raw: Any = None  #: provider response object, for debugging


@dataclass
class Message:
    """A turn in the conversation the agent maintains.

    ``role`` is one of ``"system"``, ``"user"``, ``"assistant"``, ``"tool"``.
    Assistant turns may carry ``tool_calls``; tool turns carry
    ``tool_results``. Each backend's ``chat()`` translates these into its own
    wire format.
    """

    role: str
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
