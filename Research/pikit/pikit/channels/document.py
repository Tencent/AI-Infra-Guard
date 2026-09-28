"""Document channel: hide the payload in a retrieved document or email body.

Models in RAG pipelines and email assistants read document/message text
verbatim. This channel plants the payload in a plausible location within
that text — a footnote, mid-body, or appended trailer.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("document")
class DocumentChannel(Channel):
    """Embed the payload in the body of a document or email.

    Parameters
    ----------
    method:
        * ``"footnote"`` — appended as a footnote-style note at the end.
        * ``"inline"`` — inserted near the middle of the body.
        * ``"appended"`` — plainly appended after the body (most naive).
    """

    def __init__(self, method: str = "footnote") -> None:
        if method not in ("footnote", "inline", "appended"):
            raise ValueError(
                "method must be 'footnote', 'inline', or 'appended'"
            )
        self.method = method

    def _taint(self, data: str, payload: str) -> str:
        if self.method == "footnote":
            return f"{data}\n\n[1] {payload}"
        if self.method == "appended":
            return f"{data}\n{payload}"
        # inline: insert at the paragraph break nearest the middle, falling
        # back to the character midpoint when there are no blank lines.
        paras = data.split("\n\n")
        if len(paras) > 1:
            mid = len(paras) // 2
            paras.insert(mid, payload)
            return "\n\n".join(paras)
        mid = len(data) // 2
        return f"{data[:mid]} {payload} {data[mid:]}"

    def taint(self, data: str, payload: str) -> str:
        return self._taint(data, payload)
