"""Real carrier files for file-mode indirect injection.

In *text mode* (the default), channels operate on plain-text representations
of data artifacts. In *file mode*, channels operate on real files — ``.html``,
``.eml``, ``.pdf``, ``.ics``, ``.csv``, ``.yaml``, etc. — producing a
tainted file whose format matches what a real agent would encounter.

This module maps each channel to its carrier file and provides helpers to
load carrier content. The actual files live alongside this module.

Attributes
----------
CARRIER_FILES:
    Map of ``channel_name -> filename`` for the default clean carrier.
"""

from __future__ import annotations

import os
from typing import Dict, Optional

_DIR = os.path.dirname(os.path.abspath(__file__))

CARRIER_FILES: Dict[str, str] = {
    "webpage": "webpage.html",
    "document": "document.md",
    "email_headers": "email.eml",
    "markdown": "document.md",
    "code_comment": "code.py",
    "skills": "SKILL.md",
    "structured_data": "structured_data.json",
    "pdf_metadata": "report.pdf",
    "log_file": "logfile.log",
    "calendar_event": "calendar.ics",
    "config_file": "config.yaml",
    "translation": "translation.txt",
    "unicode_hidden": "unicode_hidden.txt",
    "spreadsheet": "spreadsheet.csv",
    "chat_message": "chat_message.txt",
    "transaction_record": "transaction_record.txt",
}


def carrier_path(channel: str) -> str:
    """Return the absolute path to the default carrier file for *channel*.

    Raises
    ------
    KeyError
        If *channel* has no registered carrier file.
    """
    filename = CARRIER_FILES[channel]
    return os.path.join(_DIR, filename)


def load_carrier(channel: str) -> str:
    """Load and return the carrier file content for *channel* as a string.

    For binary formats (PDF, spreadsheet), the text representation used in
    text mode is returned so callers can switch between modes easily.
    """
    path = carrier_path(channel)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def load_carrier_bytes(channel: str) -> bytes:
    """Load and return the carrier file content for *channel* as raw bytes."""
    path = carrier_path(channel)
    with open(path, "rb") as f:
        return f.read()


__all__ = [
    "CARRIER_FILES",
    "carrier_path",
    "load_carrier",
    "load_carrier_bytes",
]
