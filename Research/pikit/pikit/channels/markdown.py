"""Markdown channel: hide the payload in Markdown a model reads.

Assistants that summarize or answer over Markdown (READMEs, wiki pages,
issues, notes) ingest source that renders differently than it reads. This
channel hides the payload where it is easy to miss on a rendered page.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("markdown")
class MarkdownChannel(Channel):
    """Embed the payload in a low-visibility part of a Markdown document.

    Parameters
    ----------
    method:
        * ``"comment"`` — an HTML comment ``<!-- payload -->`` (not rendered).
        * ``"link_title"`` — the title attribute of an inline link.
        * ``"reference"`` — a trailing reference-style link definition.
    """

    def __init__(self, method: str = "comment") -> None:
        if method not in ("comment", "link_title", "reference"):
            raise ValueError(
                "method must be 'comment', 'link_title', or 'reference'"
            )
        self.method = method

    def _hide(self, payload: str) -> str:
        if self.method == "comment":
            return f"<!-- {payload} -->"
        if self.method == "link_title":
            return f'[docs](https://example.com "{payload}")'
        return f'[ref]: https://example.com "{payload}"'

    def taint(self, data: str, payload: str) -> str:
        return f"{data}\n\n{self._hide(payload)}"
