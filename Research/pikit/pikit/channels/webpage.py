"""Webpage channel: hide the payload inside HTML a model scrapes/reads.

Models that summarize or answer questions over fetched web pages ingest the
raw HTML, including parts a human browser never renders. This channel hides
the payload in such a region so it is invisible on screen yet present in the
text the model processes.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("webpage")
class WebpageChannel(Channel):
    """Embed the payload in a non-rendered region of an HTML page.

    Parameters
    ----------
    method:
        * ``"comment"`` — inside an HTML comment ``<!-- payload -->``.
        * ``"hidden_div"`` — a ``display:none`` div.
        * ``"alt_attr"`` — the ``alt`` text of an ``<img>``.
    """

    def __init__(self, method: str = "comment") -> None:
        if method not in ("comment", "hidden_div", "alt_attr"):
            raise ValueError(
                "method must be 'comment', 'hidden_div', or 'alt_attr'"
            )
        self.method = method

    def _hide(self, payload: str) -> str:
        if self.method == "comment":
            return f"<!-- {payload} -->"
        if self.method == "hidden_div":
            return f'<div style="display:none">{payload}</div>'
        return f'<img src="x.png" alt="{payload}">'

    def taint(self, data: str, payload: str) -> str:
        # Splice the hidden element just before </body> when present,
        # otherwise append it to the page so it still reaches the model.
        hidden = self._hide(payload)
        lower = data.lower()
        idx = lower.rfind("</body>")
        if idx != -1:
            return data[:idx] + hidden + "\n" + data[idx:]
        return f"{data}\n{hidden}"
