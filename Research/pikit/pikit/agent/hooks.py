"""Defense insertion points for agents.

The same prevention-style :class:`~pikit.base.Defense` objects used for
direct injection can be slotted into three points of an agent's data flow.
The most valuable for *indirect* injection is ``tool_result`` — the layer
through which an attacker's tainted artifact re-enters the model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..base import Defense


@dataclass
class DefenseHooks:
    """Optional defenses applied at three points of the agent loop.

    Parameters
    ----------
    system:
        Hardens the system prompt (defends against the model being talked
        out of its instructions).
    tool_result:
        Hardens untrusted tool output before it re-enters the model — the
        key defense position for indirect injection.
    user:
        Hardens the incoming user message (defends against direct injection).
    """

    system: Optional[Defense] = None
    tool_result: Optional[Defense] = None
    user: Optional[Defense] = None

    def on_system(self, prompt: Optional[str]) -> Optional[str]:
        if self.system and prompt:
            return self.system.apply(prompt)
        return prompt

    def on_tool_result(self, data: str, tool_name: str) -> str:
        if self.tool_result:
            return self.tool_result.apply(data)
        return data

    def on_user(self, message: str) -> str:
        if self.user:
            return self.user.apply(message)
        return message
