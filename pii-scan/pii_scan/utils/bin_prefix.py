"""Issuer (BIN/IIN) prefix whitelist for bank card numbers.

Only used to raise confidence: a number that passes Luhn but matches no known
issuer is still reported, at ``low`` confidence.
"""

# (prefix, match) pairs by leading digits; Mastercard 2221-2720 is handled
# numerically below.
_BINS = (
    ("4",),                                   # Visa
    ("51",), ("52",), ("53",), ("54",), ("55",),  # Mastercard 51-55
    ("34",), ("37",),                         # American Express
    ("6011",),                                # Discover
    ("644",), ("645",), ("646",), ("647",), ("648",), ("649",),  # Discover
    ("65",),                                  # Discover
    ("62",),                                  # UnionPay
    ("30",), ("36",), ("38",),                # Diners Club
)


def card_bin_known(number: str) -> bool:
    n = "".join(c for c in number if c.isdigit())
    if len(n) >= 4 and n[:4].isdigit() and 2221 <= int(n[:4]) <= 2720:
        return True  # Mastercard 2221-2720
    for (prefix,) in _BINS:
        if n.startswith(prefix):
            return True
    return False
