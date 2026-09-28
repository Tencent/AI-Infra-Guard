"""Escape-character attack: use newlines/control chars to visually break out.

By inserting several newlines (and optionally a carriage return), the
injected task appears to start a fresh, separate context, encouraging the
model to treat it as a new top-level instruction rather than data.
"""

from __future__ import annotations

from ..base import Attack
from . import register


@register("escape")
class EscapeCharacterAttack(Attack):
    """Separate the injected task with escape/newline characters.

    Parameters
    ----------
    escape:
        The sequence inserted between the prompt and the injected task.
        Defaults to a few newlines, which is the classic form.
    """

    def __init__(self, escape: str = "\n\n\n") -> None:
        self.escape = escape

    def inject(self, prompt: str, injected_task: str) -> str:
        return f"{prompt}{self.escape}{injected_task}"
