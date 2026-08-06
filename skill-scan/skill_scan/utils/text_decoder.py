"""Bounded text decoding for files controlled by a scanned skill."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

import chardet

MAX_TEXT_FILE_BYTES = 4 * 1024 * 1024


class TextDecodeError(UnicodeError):
    """Raised when bytes cannot be treated as text safely."""


@dataclass(frozen=True)
class DecodedText:
    text: str
    encoding: str
    recovered_text: str | None = None
    recovery: str | None = None

    @property
    def has_mojibake(self) -> bool:
        return self.recovered_text is not None


def _is_likely_text(text: str) -> bool:
    if not text:
        return True
    controls = sum(
        char not in "\n\r\t" and unicodedata.category(char) in {"Cc", "Cs", "Cn"}
        for char in text
    )
    return controls / len(text) <= 0.02


def _decode_non_utf8(raw: bytes) -> tuple[str, str]:
    detected = chardet.detect(raw)
    encoding = detected.get("encoding")
    confidence = float(detected.get("confidence") or 0.0)

    # chardet can misclassify short GBK text. Keep one narrow fallback rather
    # than generating several candidate decodings.
    if confidence < 0.8:
        try:
            text = raw.decode("gb18030")
        except UnicodeDecodeError:
            pass
        else:
            has_cjk = any("\u3400" <= char <= "\u9fff" for char in text)
            if has_cjk and _is_likely_text(text):
                return text, "gb18030"

    if not encoding or confidence < 0.5:
        raise TextDecodeError("No reliable text encoding was detected")
    try:
        text = raw.decode(encoding)
    except (LookupError, UnicodeDecodeError) as exc:
        raise TextDecodeError("Detected encoding could not decode the file") from exc
    if not _is_likely_text(text):
        raise TextDecodeError("Decoded content contains binary control characters")
    return text, encoding


def _ascii_ratio(text: str) -> float:
    if not text:
        return 0.0
    readable = sum(char in "\n\r\t" or " " <= char <= "~" for char in text)
    return readable / len(text)


def _recover_utf16_mojibake(stored: str) -> tuple[str | None, str | None]:
    if stored.isascii():
        return None, None

    suspicious = any(unicodedata.category(char) in {"Cf", "Co"} for char in stored)
    for source in ("utf-16-le", "utf-16-be"):
        try:
            recovered = stored.encode(source).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        readability_gain = _ascii_ratio(recovered) - _ascii_ratio(stored)
        if (
            recovered != stored
            and recovered.strip()
            and _is_likely_text(recovered)
            and (suspicious or readability_gain >= 0.25)
        ):
            return recovered, f"{source} -> utf-8"
    return None, None


def decode_text_bytes(raw: bytes) -> DecodedText:
    if len(raw) > MAX_TEXT_FILE_BYTES:
        raise TextDecodeError(f"File exceeds the {MAX_TEXT_FILE_BYTES}-byte decoding limit")

    try:
        text = raw.decode("utf-8-sig")
        encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    except UnicodeDecodeError:
        text, encoding = _decode_non_utf8(raw)

    if not _is_likely_text(text):
        raise TextDecodeError("Decoded content contains binary control characters")

    recovered_text = recovery = None
    if encoding in {"utf-8", "utf-8-sig"}:
        recovered_text, recovery = _recover_utf16_mojibake(text)
    return DecodedText(text, encoding, recovered_text, recovery)


def read_text_file(path: str) -> DecodedText:
    with open(path, "rb") as file:
        return decode_text_bytes(file.read(MAX_TEXT_FILE_BYTES + 1))
