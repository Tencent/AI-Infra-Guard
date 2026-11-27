import re

from ..report.models import Hit

TYPE = "phone"
PRIORITY = 2

# Chinese mainland mobile: 1 + [3-9] + 9 digits, not embedded in a longer run.
_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def _build_prefixes():
    s = set()
    for p in range(130, 140):
        s.add(str(p))
    s.update({"145", "146", "147", "148", "149"})
    s.update({"150", "151", "152", "153", "155", "156", "157", "158", "159"})
    s.update({"165", "166", "167"})
    for p in range(170, 179):
        s.add(str(p))
    for p in range(180, 190):
        s.add(str(p))
    s.update({"190", "191", "192", "193", "195", "196", "197", "198", "199"})
    return frozenset(s)


# Known allocated mobile prefixes -> high confidence; anything else (reserved or
# IoT/data segments such as 140-144, 154) -> low, so the default threshold drops
# it. This is a curated list and may miss future segments; unknown ones stay low.
_VALID_PREFIXES = _build_prefixes()


def recognize(text: str):
    for m in _RE.finditer(text):
        value = m.group(0)
        confidence = "high" if value[:3] in _VALID_PREFIXES else "low"
        yield Hit(TYPE, m.start(), m.end(), confidence, value)
