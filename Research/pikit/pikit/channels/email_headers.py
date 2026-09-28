"""Email-header channel: hide the payload inside email header fields.

The existing ``document`` channel hides payloads in the email *body*.
This channel targets the *headers* — X-headers, Reply-To, Subject, and
custom fields. Email assistants and triage agents that parse headers
for routing, filtering, or display ingest them verbatim, making headers
an effective indirect-injection surface distinct from the body.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("email_headers")
class EmailHeadersChannel(Channel):
    """Embed the payload in an email header field.

    Works on a plain-text email representation (headers followed by a
    blank line and the body), which is what an agent's email-parsing
    tool would produce after MIME decoding.

    Parameters
    ----------
    field:
        * ``"x_header"`` — a custom ``X-Note`` header (default).
        * ``"reply_to"`` — the ``Reply-To`` header.
        * ``"subject"`` — appended to the ``Subject`` header.
        * ``"custom"`` — a fully custom ``X-Instructions`` header.
    """

    def __init__(self, field: str = "x_header") -> None:
        if field not in ("x_header", "reply_to", "subject", "custom"):
            raise ValueError(
                "field must be 'x_header', 'reply_to', 'subject', or 'custom'"
            )
        self.field = field

    def _header_name(self) -> str:
        return {
            "x_header": "X-Note",
            "reply_to": "Reply-To",
            "subject": "Subject",
            "custom": "X-Instructions",
        }[self.field]

    def taint(self, data: str, payload: str) -> str:
        lines = data.splitlines()
        header_end = len(lines)
        # Find the blank line separating headers from body.
        for i, line in enumerate(lines):
            if line.strip() == "":
                header_end = i
                break

        header_name = self._header_name()

        if self.field == "subject":
            # Append to existing Subject or add a new one.
            injected = False
            for i in range(header_end):
                if lines[i].strip().startswith("Subject:"):
                    lines[i] = f"{lines[i]} {payload}"
                    injected = True
                    break
            if not injected:
                lines.insert(header_end, f"Subject: {payload}")
        else:
            # Insert the new header just before the blank line.
            one_line = " ".join(payload.splitlines())
            lines.insert(header_end, f"{header_name}: {one_line}")

        return "\n".join(lines)
