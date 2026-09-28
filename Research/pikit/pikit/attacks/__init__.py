"""Prompt-injection attacks.

Each attack subclasses :class:`pikit.base.Attack` and registers itself
under a short key. Import this package to populate the registry, then use
``attacks.get(key)`` / ``attacks.list()``.

References
----------
Most techniques here follow the formalization in Liu et al.,
"Formalizing and Benchmarking Prompt Injection Attacks and Defenses"
(USENIX Security 2024), a.k.a. *Open Prompt Injection*.
"""

from __future__ import annotations

from ..registry import Registry
from ..base import Attack

registry: Registry[Attack] = Registry("attack")
register = registry.register
get = registry.get
list = registry.list  # noqa: A001 - mirror dict-like API on purpose

# Importing the modules triggers their @register decorators.
from . import (  # noqa: E402,F401
    naive,
    escape,
    context_ignoring,
    fake_completion,
    combined,
    payload_splitting,
    obfuscation,
    prefix_injection,
    format_confusion,
    context_flooding,
    cross_channel,
    important_instructions,
    stealth_instruction,
)

__all__ = ["registry", "register", "get", "list", "Attack"]
