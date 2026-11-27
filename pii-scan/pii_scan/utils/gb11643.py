"""Chinese resident ID number validation (GB 11643, ISO 7064 MOD 11-2)."""
import datetime

_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_CHECK = ("1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2")


def _valid_birth(yyyymmdd: str) -> bool:
    try:
        year = int(yyyymmdd[0:4])
        month = int(yyyymmdd[4:6])
        day = int(yyyymmdd[6:8])
    except ValueError:
        return False
    if not (1900 <= year <= 2100):
        return False
    try:
        datetime.date(year, month, day)
    except ValueError:
        return False
    return True


def cn_id_valid(id_number: str) -> bool:
    """Validate an 18-character Chinese ID number (check digit may be 'X')."""
    s = id_number.strip().upper()
    if len(s) != 18:
        return False
    body, check = s[:17], s[17]
    if not body.isdigit():
        return False
    if not _valid_birth(body[6:14]):
        return False
    total = sum(int(c) * w for c, w in zip(body, _WEIGHTS))
    return _CHECK[total % 11] == check
