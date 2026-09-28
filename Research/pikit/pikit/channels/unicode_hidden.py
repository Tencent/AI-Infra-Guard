"""Unicode-hidden channel: encode the payload as invisible characters.

The payload is rendered as characters that occupy no visible space, so the
tainted data looks identical to the clean data to a human, yet the model
still receives the hidden instruction in its token stream.

Two schemes are provided, both losslessly decodable (see :func:`decode`):

* ``zero_width`` — each payload byte becomes 8 zero-width characters
  (ZWSP for 0, ZWNJ for 1).
* ``unicode_tags`` — each ASCII char is mapped into the Unicode *Tags*
  block (U+E0000+), which renders as nothing in most contexts.
"""

from __future__ import annotations

from ..base import Channel
from . import register

_ZERO = "\u200b"  # ZERO WIDTH SPACE -> bit 0
_ONE = "\u200c"  # ZERO WIDTH NON-JOINER -> bit 1
_TAG_BASE = 0xE0000  # Unicode Tags block base


def _to_zero_width(payload: str) -> str:
    bits = "".join(f"{byte:08b}" for byte in payload.encode("utf-8"))
    return "".join(_ONE if b == "1" else _ZERO for b in bits)


def _to_unicode_tags(payload: str) -> str:
    # Only ASCII maps cleanly into the tag block; non-ASCII is passed through.
    return "".join(
        chr(_TAG_BASE + ord(c)) if ord(c) < 0x80 else c for c in payload
    )


def decode(text: str) -> str:
    """Recover a payload hidden by either scheme from ``text``.

    Useful in tests and for defenders building detectors. Characters that
    are not part of a hidden payload are ignored.
    """
    # Unicode tags first.
    tagged = [
        chr(ord(c) - _TAG_BASE)
        for c in text
        if _TAG_BASE <= ord(c) < _TAG_BASE + 0x80
    ]
    if tagged:
        return "".join(tagged)
    # Zero-width bits.
    bits = "".join(
        "1" if c == _ONE else "0" for c in text if c in (_ZERO, _ONE)
    )
    if not bits:
        return ""
    by = bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits) - 7, 8))
    return by.decode("utf-8", errors="ignore")


@register("unicode_hidden")
class UnicodeHiddenChannel(Channel):
    """Embed the payload as invisible Unicode characters within the data.

    Parameters
    ----------
    scheme:
        ``"zero_width"`` (default) or ``"unicode_tags"``.
    position:
        Where to splice the hidden run: ``"end"`` (default), ``"start"``,
        or ``"middle"``.
    """

    def __init__(self, scheme: str = "zero_width", position: str = "end") -> None:
        if scheme not in ("zero_width", "unicode_tags"):
            raise ValueError("scheme must be 'zero_width' or 'unicode_tags'")
        if position not in ("start", "middle", "end"):
            raise ValueError("position must be 'start', 'middle', or 'end'")
        self.scheme = scheme
        self.position = position

    def _encode(self, payload: str) -> str:
        if self.scheme == "zero_width":
            return _to_zero_width(payload)
        return _to_unicode_tags(payload)

    def taint(self, data: str, payload: str) -> str:
        hidden = self._encode(payload)
        if self.position == "start":
            return hidden + data
        if self.position == "end":
            return data + hidden
        mid = len(data) // 2
        return data[:mid] + hidden + data[mid:]
