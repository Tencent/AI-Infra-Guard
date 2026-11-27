"""Text loading: size cap, binary rejection, UTF-8 then GB18030 decoding.

Standard library only (no ``chardet``); this keeps the scanner runnable under
``uv run --no-project`` where a new package's dependencies are not installed.
"""
import os
from typing import Optional, Tuple

MAX_TEXT_FILE_BYTES = 4 * 1024 * 1024  # align with skill-scan text_decoder

_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030")


def is_binary(data: bytes) -> bool:
    sample = data[:8192]
    if b"\x00" in sample:
        return True
    if not sample:
        return False
    control = sum(1 for b in sample if b < 9 or b in (11, 12) or (13 < b < 32))
    return control / len(sample) > 0.30


def decode_bytes(data: bytes) -> Tuple[Optional[str], Optional[str]]:
    """Return (text, None) on success, or (None, reason) on failure."""
    for enc in _ENCODINGS:
        try:
            return data.decode(enc), None
        except UnicodeDecodeError:
            continue
    return None, "undecodable"


def read_text_file(path: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (text, None) for a scannable file, or (None, status).

    status is one of: ``filtered`` (too large / binary), ``failed``
    (undecodable / read error).
    """
    try:
        size = os.path.getsize(path)
    except OSError:
        return None, "failed"
    if size > MAX_TEXT_FILE_BYTES:
        return None, "filtered"
    try:
        with open(path, "rb") as fh:
            data = fh.read(MAX_TEXT_FILE_BYTES + 1)
    except OSError:
        return None, "failed"
    if len(data) > MAX_TEXT_FILE_BYTES:
        return None, "filtered"
    if is_binary(data):
        return None, "filtered"
    text, err = decode_bytes(data)
    if text is None:
        return None, "failed"
    return text, None
