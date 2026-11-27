from pii_scan import scan_text


def test_masking_no_raw():
    f = scan_text("phone 13800138000")[0]
    assert f.masked_sample == "138*****000"
    assert "13800138000" not in f.masked_sample


def test_cjk_column_is_code_points():
    f = [x for x in scan_text("中文 13800138000") if x.type == "phone"][0]
    assert f.line == 1
    assert f.column == 4          # "中文 " is 3 code points -> phone at column 4


def test_multiline_line_column():
    f = scan_text("a\n13800138000")[0]
    assert f.line == 2 and f.column == 1


def test_min_confidence_filters_low():
    assert scan_text("0000000000000000") == []
    low = scan_text("0000000000000000", min_confidence="low")
    assert low and low[0].confidence == "low"


def test_enabled_subset():
    assert scan_text("a@b.com", enabled=[]) == []
    assert scan_text("a@b.com", enabled=["email"])[0].type == "email"
