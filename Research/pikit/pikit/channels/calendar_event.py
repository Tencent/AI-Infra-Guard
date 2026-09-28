"""Calendar-event channel: hide the payload inside a calendar invite.

Scheduling agents that read .ics files or calendar APIs process event
metadata — title, description, location, attendee notes. A payload
planted in one of these fields is ingested verbatim when the agent
summarises, triages, or acts on the event.

**File mode**: :meth:`taint_file` operates on real ``.ics`` files using
iCalendar standard field names (``SUMMARY``, ``DESCRIPTION``, ``LOCATION``,
``NOTE``).
"""

from __future__ import annotations

import os

from ..base import Channel
from . import register


@register("calendar_event")
class CalendarEventChannel(Channel):
    """Embed the payload in a calendar event field.

    Works on a plain-text calendar event representation (field ``key:
    value`` lines), which is what an agent's calendar tool would return
    after parsing an .ics file or calling a calendar API.

    Parameters
    ----------
    field:
        * ``"title"`` — the event ``Title`` (default).
        * ``"description"`` — the event ``Description``.
        * ``"location"`` — the event ``Location``.
        * ``"attendee_note"`` — an attendee ``Note`` field.
    """

    _FIELDS = ("title", "description", "location", "attendee_note")

    _FIELD_MAP = {
        "title": "Title",
        "description": "Description",
        "location": "Location",
        "attendee_note": "Note",
    }

    # iCalendar (.ics) standard property names.
    _ICS_FIELD_MAP = {
        "title": "SUMMARY",
        "description": "DESCRIPTION",
        "location": "LOCATION",
        "attendee_note": "NOTE",
    }

    def __init__(self, field: str = "title") -> None:
        if field not in self._FIELDS:
            raise ValueError(
                "field must be 'title', 'description', 'location', or 'attendee_note'"
            )
        self.field = field

    def taint(self, data: str, payload: str) -> str:
        field_name = self._FIELD_MAP[self.field]
        lines = data.splitlines()
        injected = False
        out = []
        for line in lines:
            if not injected and line.strip().startswith(f"{field_name}:"):
                if self.field == "title":
                    out.append(f"{field_name}: {payload}")
                else:
                    out.append(f"{line} {payload}")
                injected = True
            else:
                out.append(line)
        if not injected:
            out.append(f"{field_name}: {payload}")
        return "\n".join(out)

    def taint_file(self, path: str, payload: str, output_path=None) -> str:
        """Inject the payload into a real ``.ics`` calendar file.

        Uses iCalendar standard property names (``SUMMARY``, ``DESCRIPTION``,
        ``LOCATION``, ``NOTE``).
        """
        ics_field = self._ICS_FIELD_MAP[self.field]
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        injected = False
        out = []
        for line in lines:
            if not injected and line.strip().upper().startswith(f"{ics_field}:"):
                if self.field == "title":
                    out.append(f"{ics_field}:{payload}")
                else:
                    out.append(f"{line} {payload}")
                injected = True
            else:
                out.append(line)
        if not injected:
            # Insert before END:VEVENT if present, else append.
            insert_text = f"{ics_field}:{payload}"
            for i, line in enumerate(out):
                if line.strip().upper() == "END:VEVENT":
                    out.insert(i, insert_text)
                    injected = True
                    break
            if not injected:
                out.append(insert_text)

        if output_path is None:
            base, ext = os.path.splitext(path)
            output_path = f"{base}.tainted{ext}"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
        return output_path