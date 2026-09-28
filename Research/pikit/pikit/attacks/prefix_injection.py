"""Prefix-injection attack: place the payload *before* the original prompt.

All other attacks in this package append the payload. Prefix injection puts
the injected instruction first, which can dominate when a model weighs
earlier tokens as the primary directive, and models the case where attacker
data is prepended to (rather than appended to) trusted content.
"""

from __future__ import annotations

from ..base import Attack
from . import register


@register("prefix_injection")
class PrefixInjectionAttack(Attack):
    """Prepend the injected task (plus a context break) before the prompt.

    Parameters
    ----------
    separator:
        Inserted between the injected task and the original prompt. A few
        newlines help the payload read as a self-contained leading directive.
    lead_in:
        Optional text placed before the injected task (e.g. a fake role or
        priority marker). Empty by default.
    """

    def __init__(self, separator: str = "\n\n", lead_in: str = "") -> None:
        self.separator = separator
        self.lead_in = lead_in

    def inject(self, prompt: str, injected_task: str) -> str:
        return f"{self.lead_in}{injected_task}{self.separator}{prompt}"
