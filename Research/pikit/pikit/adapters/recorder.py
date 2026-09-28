"""Shared conversion of framework events into a pikit :class:`Trace`."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..agent.base import Trace, TraceStep


class TraceRecorder:
    """Build a structured pikit trace from external-agent events."""

    def __init__(self) -> None:
        self.trace = Trace()

    def system(self, text: Optional[str]) -> None:
        if text:
            self.trace.add(TraceStep("system", text=text))

    def user(self, text: str) -> None:
        self.trace.add(TraceStep("user", text=text))

    def model(self, text: str = "") -> None:
        self.trace.add(TraceStep("model", text=text))

    def tool_call(
        self,
        tool_name: str,
        args: Optional[Dict[str, Any]] = None,
        *,
        is_sink: bool = False,
    ) -> None:
        self.trace.add(
            TraceStep(
                "tool_call",
                tool_name=tool_name,
                args=dict(args or {}),
                is_sink=is_sink,
            )
        )

    def tool_result(
        self,
        tool_name: str,
        content: Any,
        *,
        tainted: bool = False,
    ) -> None:
        self.trace.add(
            TraceStep(
                "tool_result",
                tool_name=tool_name,
                content=str(content),
                tainted=tainted,
            )
        )

    def finish(self, text: Any) -> Trace:
        final_text = str(text or "")
        self.model(final_text)
        self.trace.final_text = final_text
        return self.trace


__all__ = ["TraceRecorder"]
