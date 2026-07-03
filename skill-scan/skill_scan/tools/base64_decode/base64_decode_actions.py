from __future__ import annotations

import base64
import re
from typing import Any

from skill_scan.tools.registry import register_tool
from skill_scan.utils.loging import logger


@register_tool(sandbox_execution=False)
def base64_decode(text: str) -> dict[str, Any]:
    """Base64-decode a string, and automatically extract and decode any suspected
    base64-encoded fragments found within the text.

    Args:
        text: The base64 string to decode, or text containing base64 fragments.
              Can be a pure base64 string or mixed text containing base64 fragments.

    Returns:
        Dict containing the list of decoded results, each with the original fragment
        and its decoded content.
    """
    results = []

    # First try decoding the whole input
    stripped = text.strip()
    direct = _try_decode(stripped)
    if direct is not None:
        results.append({
            'input': stripped,
            'decoded': direct,
        })

    # Then extract all suspected base64 fragments from the text (length >= 16 to avoid false positives on short words)
    # base64 character set: A-Z a-z 0-9 + / = plus the URL-safe variant - _
    pattern = re.compile(r'[A-Za-z0-9+/\-_]{16,}={0,2}')
    for match in pattern.finditer(text):
        fragment = match.group(0)
        # Skip fragments already decoded as part of the whole string (avoid duplicates)
        if fragment == stripped and direct is not None:
            continue
        decoded = _try_decode(fragment)
        if decoded is not None:
            results.append({
                'input': fragment,
                'decoded': decoded,
                'source': 'extracted',
            })

    if not results:
        logger.info(f'base64_decode: no valid base64 found in input (len={len(text)})')
        return {
            'success': False,
            'message': 'No valid base64-encoded content found',
        }

    logger.info(f'base64_decode: decoded {len(results)} fragment(s)')
    return {
        'success': True,
        'results': results,
        'count': len(results),
    }


def _try_decode(s: str) -> str | None:
    """Try to base64-decode a string; return the result if successful and printable, else None."""
    # Pad the string
    padded = s + '=' * (-len(s) % 4)
    for decode_fn in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            raw = decode_fn(padded)
            text = raw.decode('utf-8')
            # Filter out garbled output: require printable characters to make up > 80%
            printable = sum(1 for c in text if c.isprintable() or c in '\n\r\t')
            if len(text) > 0 and printable / len(text) > 0.8:
                return text
        except Exception:
            continue
    return None
