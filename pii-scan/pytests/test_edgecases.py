import json

from pii_scan import scan_text
from pii_scan.main import run
from pii_scan.recognizers import email as email_rec
from pii_scan.recognizers import phone as phone_rec
from pii_scan.scanner import _mask


def _lcs(a, b):
    best = 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def test_mask_invariant_no_long_common_substring():
    samples = [
        "11010519491231002X",
        "4111111111111111",
        "13800138000",
        "john.doe@example.com",
    ]
    for s in samples:
        findings = scan_text(s)
        assert findings, s
        for f in findings:
            assert s not in f.masked_sample          # full raw never shown
            assert _lcs(f.masked_sample, s) < 4      # <=3 contiguous chars retained


def test_email_wins_over_inner_phone():
    types = [f.type for f in scan_text("13800138000@example.com")]
    assert types == ["email"], types


def test_email_invalid_domains_rejected():
    assert list(email_rec.recognize("a@b..com")) == []
    assert list(email_rec.recognize("a@-b.com")) == []
    assert list(email_rec.recognize("a@b-.com")) == []
    assert list(email_rec.recognize("a@b.com")) != []


def test_phone_segment_confidence():
    def conf(num):
        return [h.confidence for h in phone_rec.recognize(num)]

    assert conf("13800138000") == ["high"]
    assert conf("14012345678") == ["low"]   # reserved 140 segment
    assert conf("15412345678") == ["low"]   # IoT 154 segment


def test_astral_emoji_column_is_code_points():
    f = [x for x in scan_text("\U0001F600 13800138000") if x.type == "phone"][0]
    assert f.column == 3   # emoji is one code point + one space


def test_short_value_masked_fully():
    assert _mask("123", "x") == "***"
    assert _mask("12", "x") == "**"


def test_no_mask_emits_raw(capsys):
    run(["--text", "phone 13800138000", "--no-mask"])
    out = capsys.readouterr().out
    assert "13800138000" in out
    assert json.loads(out)["findings"][0]["raw_sample"] == "13800138000"


def test_min_confidence_gate(capsys):
    assert run(["--text", "0000000000000000"]) == 0            # low filtered
    assert run(["--text", "0000000000000000", "--min-confidence", "low"]) == 1


def test_oversize_file_counted_filtered(tmp_path):
    (tmp_path / "big.txt").write_bytes(b"13800138000\n" * 400000)  # > 4 MiB
    (tmp_path / "c.txt").write_text("ok", encoding="utf-8")
    code = run(["--path", str(tmp_path), "-o", str(tmp_path / "out.json")])
    doc = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert doc["summary"]["filtered"] >= 1
    assert code == 0


def test_sarif_determinism_and_properties(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("phone 13800138000", encoding="utf-8")
    o1, o2 = tmp_path / "a.sarif", tmp_path / "b.sarif"
    run(["--path", str(src), "--format", "sarif", "-o", str(o1)])
    run(["--path", str(src), "--format", "sarif", "-o", str(o2)])
    assert o1.read_bytes() == o2.read_bytes()
    doc = json.loads(o1.read_text(encoding="utf-8"))
    props = doc["runs"][0]["properties"]
    assert props["summary"]["scanned_ok"] == 1
    assert "active_recognizers" in props
