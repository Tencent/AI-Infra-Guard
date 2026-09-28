"""Chat-message channel: hide the payload inside an IM/Slack message.

Models an indirect-injection vector where the payload is embedded in a
chat message (Slack, Teams, Discord, etc.). The message looks normal in
the UI but contains hidden instructions the model reads when processing
the channel history.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("chat_message")
class ChatMessageChannel(Channel):
    """Embed the payload in a chat/IM message.

    Parameters
    ----------
    method:
        * ``"inline"`` — payload inline in the message text.
        * ``"mention"`` — payload disguised as a @mention/bot command.
        * ``"thread_reply"`` — payload in a threaded reply.
    """

    def __init__(self, method: str = "inline") -> None:
        if method not in ("inline", "mention", "thread_reply"):
            raise ValueError(
                "method must be 'inline', 'mention', or 'thread_reply'"
            )
        self.method = method

    def _hide(self, payload: str) -> str:
        if self.method == "inline":
            return payload
        if self.method == "mention":
            return f"@system-bot {payload}"
        # thread_reply
        return f"  [reply] {payload}"

    def taint(self, data: str, payload: str) -> str:
        hidden = self._hide(payload)
        # Append the tainted message to the channel history.
        # If data already looks like a message list, append a new entry;
        # otherwise wrap it.
        lines = data.strip().splitlines()
        if lines and lines[0].startswith("["):
            # Looks like a message log — append a new message line.
            return f"{data.rstrip()}\n[2025-07-01 11:00] attacker: {hidden}"
        return f"{data}\n\n[Chat message]\n{hidden}"
