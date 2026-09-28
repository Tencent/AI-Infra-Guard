"""Naive attack: just concatenate the injected task onto the prompt."""

from __future__ import annotations

from ..base import Attack
from . import register


@register("naive")
class NaiveAttack(Attack):
    """Append the injected task directly after the prompt.

    The simplest possible injection and a useful lower-bound baseline:
    no separators, no deception, just appended text.
    """

    def __init__(self, separator: str = " ") -> None:
        self.separator = separator

    def inject(self, prompt: str, injected_task: str) -> str:
        return f"{prompt}{self.separator}{injected_task}"
