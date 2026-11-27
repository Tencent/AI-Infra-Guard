import re

from ..report.models import Hit

TYPE = "email"
PRIORITY = 2

_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _valid_local(local: str) -> bool:
    return bool(local) and not local.startswith(".") and not local.endswith(".") and ".." not in local


def _valid_domain(domain: str) -> bool:
    if ".." in domain:
        return False
    for label in domain.split("."):
        if not label or label.startswith("-") or label.endswith("-"):
            return False
    return True


def recognize(text: str):
    for m in _RE.finditer(text):
        value = m.group(0)
        if "\n" in value:
            continue
        local, _, domain = value.partition("@")
        if _valid_local(local) and _valid_domain(domain):
            yield Hit(TYPE, m.start(), m.end(), "high", value)
