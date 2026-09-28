"""Prevention-style prompt-injection defenses.

Each defense subclasses :class:`pikit.base.Defense` and registers itself
under a short key. These are all *prevention* techniques: pure prompt
transforms that need no extra model call. (Detection-style defenses, which
return a judgement, are intentionally out of scope for this release.)

Import this package to populate the registry, then use
``defenses.get(key)`` / ``defenses.list()``.
"""

from __future__ import annotations

from ..registry import Registry
from ..base import Defense

registry: Registry[Defense] = Registry("defense")
register = registry.register
get = registry.get
list = registry.list  # noqa: A001 - mirror dict-like API on purpose

# Importing the modules triggers their @register decorators.
from . import (  # noqa: E402,F401
    delimiters,
    sandwich,
    instructional,
    spotlighting,
    random_sequence_enclosure,
    retokenization,
    instruction_hierarchy,
    few_shot_warning,
    self_reminder,
)

__all__ = ["registry", "register", "get", "list", "Defense"]
