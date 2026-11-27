import re

from ..report.models import Hit
from ..utils.bin_prefix import card_bin_known
from ..utils.luhn import luhn_valid

TYPE = "bank_card"
# cn_id must outrank bank_card on an identical span: an 18-digit CN ID may also
# pass Luhn, and it is the more specific, checksum+date-validated type.
PRIORITY = 1

# 13-19 digit run, not embedded in a longer digit run.
_RE = re.compile(r"(?<!\d)\d{13,19}(?!\d)")


def recognize(text: str):
    for m in _RE.finditer(text):
        value = m.group(0)
        # A 17-digit run immediately followed by 'X'/'x' is the numeric body of an
        # 18-character ID number, not a card.
        if len(value) == 17 and m.end() < len(text) and text[m.end()] in ("X", "x"):
            continue
        if not luhn_valid(value):
            continue
        confidence = "high" if card_bin_known(value) else "low"
        yield Hit(TYPE, m.start(), m.end(), confidence, value)
