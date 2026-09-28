"""Log-file channel: hide the payload inside system / application logs.

Debug and monitoring agents read log files to diagnose issues. A payload
planted in a log entry — disguised as a warning, an error trace, or a
system message — blends in with the noise and is processed verbatim by
the model.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("log_file")
class LogFileChannel(Channel):
    """Embed the payload as a log entry.

    Parameters
    ----------
    level:
        The log level prefix for the fake entry:
        * ``"info"`` — ``[INFO] payload``
        * ``"warn"`` — ``[WARN] payload``
        * ``"error"`` — ``[ERROR] payload``
        * ``"debug"`` — ``[DEBUG] payload``
    position:
        Where to splice the fake entry: ``"end"`` (default) or ``"middle"``.
    """

    _LEVELS = {"info": "[INFO]", "warn": "[WARN]", "error": "[ERROR]", "debug": "[DEBUG]"}

    def __init__(self, level: str = "warn", position: str = "end") -> None:
        if level not in self._LEVELS:
            raise ValueError("level must be 'info', 'warn', 'error', or 'debug'")
        if position not in ("end", "middle"):
            raise ValueError("position must be 'end' or 'middle'")
        self.level = level
        self.position = position

    def _make_entry(self, payload: str) -> str:
        tag = self._LEVELS[self.level]
        # Collapse payload to a single line.
        one_line = " ".join(payload.splitlines())
        return f"2024-01-15T10:30:00Z {tag} {one_line}"

    def taint(self, data: str, payload: str) -> str:
        entry = self._make_entry(payload)
        if self.position == "middle":
            lines = data.splitlines()
            if len(lines) > 1:
                mid = len(lines) // 2
                lines.insert(mid, entry)
                return "\n".join(lines)
        return f"{data}\n{entry}" if data else entry
