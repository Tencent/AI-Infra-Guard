"""Luhn (mod 10) checksum, ISO/IEC 7812-1, used by bank card numbers."""


def luhn_valid(number: str) -> bool:
    """Return True if the digit string passes the Luhn check.

    Non-digits are ignored; the caller is expected to pass a run that is
    already digit-only and of a plausible length (13-19).
    """
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 12:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0
