"""Recognizer registry.

Each recognizer module exposes ``TYPE``, ``PRIORITY`` and ``recognize(text)``.
Lower PRIORITY wins on overlapping spans (checksum-validated identifier types
before generic contact types).
"""
from . import bank_card, cn_id, email, phone

# (type, priority, recognize)
REGISTRY = (
    (cn_id.TYPE, cn_id.PRIORITY, cn_id.recognize),
    (bank_card.TYPE, bank_card.PRIORITY, bank_card.recognize),
    (phone.TYPE, phone.PRIORITY, phone.recognize),
    (email.TYPE, email.PRIORITY, email.recognize),
)

DEFAULT_TYPES = tuple(item[0] for item in REGISTRY)


def get_recognizers(enabled=None):
    if enabled is None:
        return REGISTRY
    wanted = set(enabled)
    return tuple(item for item in REGISTRY if item[0] in wanted)
