import re

from ..report.models import Hit
from ..utils.gb11643 import cn_id_valid

TYPE = "cn_id"
PRIORITY = 0

# 18 characters: 17 digits + check digit ('X' allowed), not part of a longer
# alphanumeric run.
_RE = re.compile(r"(?<![0-9A-Za-z])[1-9]\d{16}[0-9Xx](?![0-9A-Za-z])")


def recognize(text: str):
    for m in _RE.finditer(text):
        value = m.group(0)
        if cn_id_valid(value):
            yield Hit(TYPE, m.start(), m.end(), "high", value)
