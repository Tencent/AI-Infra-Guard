"""An offline echo target — a **test fixture**, not a demo backend.

This target only echoes its input and never executes an injection, so it
**cannot demonstrate whether an attack works** — using it to "show" an attack
would misrepresent results. Its sole purpose is the offline test suite:
deterministic, no API key, no network, no token cost. To actually observe an
attack against an agent, use a real model via :func:`~pikit.targets.get_target`
(``openai:`` / ``anthropic:`` / ``hf:``); see ``demos/live_matrix``.

The :meth:`chat` method supports two offline modes so the function-calling
loop is fully testable:

* **Scripted** — pass ``script=[ChatResponse, ...]``; each ``chat()`` call
  pops the next response. Lets a test drive an exact tool-call sequence.
* **Heuristic** — with no script, if tools are offered and none has been
  called yet, it calls the first tool; once a tool result is in history it
  returns a final text echoing what it saw. Enough to exercise the loop in
  tests.
"""

from __future__ import annotations

from typing import List, Optional

from .base import Target
from .types import ChatResponse, Message, ToolCall


class MockTarget(Target):
    """Returns a deterministic echo of what it received.

    Parameters
    ----------
    prefix:
        Text prepended to the echoed prompt. Handy for asserting in tests
        that the full pipeline reached the target.
    script:
        Optional list of :class:`ChatResponse` to return from successive
        ``chat()`` calls, for deterministic tool-loop tests.
    """

    name = "mock"

    def __init__(
        self,
        prefix: str = "[mock] ",
        script: Optional[List[ChatResponse]] = None,
    ) -> None:
        self.prefix = prefix
        self._script = list(script) if script else None
        self._calls = 0

    def query(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        parts = []
        if system:
            parts.append(f"<system>{system}</system>")
        parts.append(prompt)
        return self.prefix + "\n".join(parts)

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[dict]] = None,
        system: Optional[str] = None,
        **kwargs,
    ) -> ChatResponse:
        self._calls += 1

        # Scripted mode: pop the next pre-baked response.
        if self._script is not None:
            if not self._script:
                return ChatResponse(text=f"{self.prefix}(script exhausted)")
            return self._script.pop(0)

        # Heuristic mode.
        already_called = any(m.role == "tool" for m in messages)
        if tools and not already_called:
            first = tools[0]["name"]
            return ChatResponse(
                text="",
                tool_calls=[ToolCall(id=f"mock-{self._calls}", name=first, args={})],
                stop_reason="tool_use",
            )
        # Echo the most recent tool result (or user message) as final text.
        seen = ""
        for m in reversed(messages):
            if m.role == "tool" and m.tool_results:
                seen = m.tool_results[-1].content
                break
            if m.role == "user":
                seen = m.content
                break
        return ChatResponse(text=f"{self.prefix}{seen}", stop_reason="end")
