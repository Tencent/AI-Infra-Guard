"""Preconfigured scenario agents with realistic toolsets and sinks."""

from __future__ import annotations

# Importing the modules triggers their @register decorators.
from . import (  # noqa: F401
    browser, coding, email_assistant, rag_qa,
    im, calendar, finance, travel, social, file_manager,
    general,
)

# Register the permissive variant (H1 hypothesis test).
from . import general_permissive  # noqa: F401

__all__ = [
    "email_assistant", "rag_qa", "browser", "coding",
    "im", "calendar", "finance", "travel", "social", "file_manager",
    "general", "general_permissive",
]
