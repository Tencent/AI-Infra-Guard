"""Indirect prompt-injection channels.

A *channel* hides an (optionally attack-worded) payload inside an external
data artifact the model later reads — a web page, a retrieved document, an
email — and returns the full prompt the target would receive. Channels are
orthogonal to attacks and compose freely (``attack × channel``).

Each channel subclasses :class:`pikit.base.Channel` and registers itself
under a short key. Import this package to populate the registry, then use
``channels.get(key)`` / ``channels.list()``.

References
----------
Indirect prompt injection was introduced by Greshake et al.,
"Not what you've signed up for: Compromising Real-World LLM-Integrated
Applications with Indirect Prompt Injection" (AISec 2023).
"""

from __future__ import annotations

from ..registry import Registry
from ..base import Channel

registry: Registry[Channel] = Registry("channel")
register = registry.register
get = registry.get
list = registry.list  # noqa: A001 - mirror dict-like API on purpose

# Importing the modules triggers their @register decorators.
from . import (  # noqa: E402,F401
    webpage,
    document,
    unicode_hidden,
    markdown,
    code_comment,
    skills,
    structured_data,
    pdf_metadata,
    log_file,
    email_headers,
    calendar_event,
    config_file,
    translation,
    spreadsheet,
    chat_message,
    transaction_record,
)

__all__ = ["registry", "register", "get", "list", "Channel"]
