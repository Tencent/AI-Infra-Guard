import json

from pii_scan import scan_text
from pii_scan.main import run
from pii_scan.recognizers import email as email_rec
from pii_scan.utils.gb11643 import cn_id_valid
from pii_scan.utils.luhn import luhn_valid

_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_CHECK = ("1", "0", "X", "9", "8", "7", "6", "5", "4", "3", "2")


def _find_double_valid_id():
    """A valid CN ID (with a digit check digit) that also passes Luhn."""
    base = "110105194912310"  # 15 digits, date 1949-12-31 valid
    for n in range(1000):
        body = base + "{:02d}".format(n % 100)  # 17 digits
        total = sum(int(c) * w for c, w in zip(body, _WEIGHTS))
        full = body + _CHECK[total % 11]
        if full[-1].isdigit() and cn_id_valid(full) and luhn_valid(full):
            return full
    return None


def test_double_valid_number_reported_as_cn_id_not_card():
    full = _find_double_valid_id()
    assert full is not None, "could not construct a double-valid number"
    types = [f.type for f in scan_text("id " + full)]
    assert types == ["cn_id"], (full, types)


def test_valid_id_ending_in_x_not_misreported_as_card():
    types = [f.type for f in scan_text("id 11010519491231002X")]
    assert types == ["cn_id"], types


def test_low_card_does_not_suppress_high_email():
    # 16 zeros is Luhn-valid (bank_card low); the email must still be reported.
    types = [f.type for f in scan_text("0000000000000000@x.com")]
    assert types == ["email"], types


def test_unknown_disable_is_usage_error():
    assert run(["--text", "x", "--disable", "bankcard"]) == 2


def test_email_local_dots_rejected():
    assert list(email_rec.recognize(".a@b.com")) == []
    assert list(email_rec.recognize("a.@b.com")) == []
    assert list(email_rec.recognize("a..b@c.com")) == []


def test_output_inside_scanned_tree_is_excluded(tmp_path):
    (tmp_path / "a.txt").write_text("phone 13800138000", encoding="utf-8")
    out = tmp_path / "out.json"
    run(["--path", str(tmp_path), "-o", str(out)])
    first = out.read_bytes()
    run(["--path", str(tmp_path), "-o", str(out)])
    second = out.read_bytes()
    assert first == second
    assert json.loads(second)["summary"]["files_total"] == 1
