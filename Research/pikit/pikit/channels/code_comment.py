"""Code-comment channel: hide the payload inside source-code comments.

Coding assistants and code-review/analysis agents read source files whole,
comments included. An instruction planted in a comment is easy for a human
reviewer to skim past but is fully present in what the model processes.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("code_comment")
class CodeCommentChannel(Channel):
    """Embed the payload in a code comment.

    Parameters
    ----------
    style:
        * ``"hash"`` — ``# payload`` (Python, shell, Ruby, YAML).
        * ``"slashes"`` — ``// payload`` (C, Java, JS, Go, Rust).
        * ``"block"`` — ``/* payload */`` (C-family block comment).
    position:
        ``"end"`` (default) appends the comment after the code; ``"start"``
        prepends it (e.g. a fake file-header directive).
    """

    def __init__(self, style: str = "hash", position: str = "end") -> None:
        if style not in ("hash", "slashes", "block"):
            raise ValueError("style must be 'hash', 'slashes', or 'block'")
        if position not in ("start", "end"):
            raise ValueError("position must be 'start' or 'end'")
        self.style = style
        self.position = position

    def _hide(self, payload: str) -> str:
        # Collapse newlines so the payload stays a single valid comment.
        one_line = " ".join(payload.splitlines())
        if self.style == "hash":
            return f"# {one_line}"
        if self.style == "slashes":
            return f"// {one_line}"
        return f"/* {one_line} */"

    def taint(self, data: str, payload: str) -> str:
        comment = self._hide(payload)
        if self.position == "start":
            return f"{comment}\n{data}"
        return f"{data}\n{comment}"
