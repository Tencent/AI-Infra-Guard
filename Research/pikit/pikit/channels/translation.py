"""Translation channel: hide the payload inside a translation tool's output.

Translation agents read source text and produce translated output. When
the source text is attacker-controlled (e.g. user-submitted content,
scraped web text), a payload planted in the source survives into the
translation output and is then processed by downstream agents that
consume the translated text.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("translation")
class TranslationChannel(Channel):
    """Embed the payload in a translation output.

    Works on a plain-text translation result representation (``Source:
    ...`` / ``Translation: ...``), which is what a translation tool would
    return to the agent.

    Parameters
    ----------
    method:
        * ``"source"`` — the payload is in the source text (default).
        * ``"translation"`` — the payload appears in the translated
          output (as if the translator was tricked into passing it
          through verbatim).
        * ``"note"`` — a translator's note appended to the output.
    """

    def __init__(self, method: str = "source") -> None:
        if method not in ("source", "translation", "note"):
            raise ValueError("method must be 'source', 'translation', or 'note'")
        self.method = method

    def taint(self, data: str, payload: str) -> str:
        lines = data.splitlines()
        out = []
        injected = False

        for line in lines:
            if not injected:
                lower = line.strip().lower()
                if self.method == "source" and lower.startswith("source:"):
                    out.append(f"{line} {payload}")
                    injected = True
                    continue
                if self.method == "translation" and lower.startswith("translation:"):
                    out.append(f"{line} {payload}")
                    injected = True
                    continue
            out.append(line)

        if not injected:
            if self.method == "source":
                out.append(f"Source: {payload}")
            elif self.method == "translation":
                out.append(f"Translation: {payload}")
            else:
                out.append(f"Translator's note: {payload}")

        if self.method == "note" and not injected:
            pass  # handled above
        elif self.method == "note":
            out.append(f"Translator's note: {' '.join(payload.splitlines())}")

        return "\n".join(out)
