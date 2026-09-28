"""Delimiter defense: wrap the untrusted data in explicit delimiters.

Surrounding external/untrusted content with quotes or XML-style tags helps
the model tell where data ends and instructions begin, so injected
instructions hidden in the data are less likely to be obeyed.
"""

from __future__ import annotations

from typing import Optional

from ..base import Defense
from . import register
from ._util import split_instruction_data


@register("delimiters")
class DelimitersDefense(Defense):
    """Wrap the untrusted data region in delimiters.

    Parameters
    ----------
    style:
        ``"xml"`` wraps data in ``<data>...</data>`` tags; ``"quotes"``
        wraps it in triple double-quotes.
    tag:
        Tag name used when ``style="xml"``.
    """

    def __init__(self, style: str = "xml", tag: str = "data") -> None:
        if style not in ("xml", "quotes"):
            raise ValueError("style must be 'xml' or 'quotes'")
        self.style = style
        self.tag = tag

    def _wrap(self, data: str) -> str:
        if self.style == "xml":
            return f"<{self.tag}>\n{data}\n</{self.tag}>"
        return f'"""\n{data}\n"""'

    def apply(self, prompt: str, instruction: Optional[str] = None) -> str:
        instr, data = split_instruction_data(prompt, instruction)
        wrapped = self._wrap(data)
        if instr:
            return f"{instr}\n{wrapped}"
        return wrapped
