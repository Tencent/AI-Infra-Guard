import json

from pii_scan.main import run


def test_text_finding_exit1_masked(capsys):
    code = run(["--text", "phone 13800138000"])
    out = capsys.readouterr().out
    assert code == 1
    assert "13800138000" not in out
    doc = json.loads(out)
    assert doc["findings"][0]["type"] == "phone"


def test_clean_exit0(capsys):
    assert run(["--text", "nothing to see"]) == 0


def test_empty_dir_exit3(tmp_path):
    assert run(["--path", str(tmp_path)]) == 3


def test_all_filtered_exit3(tmp_path):
    (tmp_path / "x.bin").write_bytes(b"\x00\x01\x02\x00")
    assert run(["--path", str(tmp_path)]) == 3


def test_file_finding_exit1(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("phone 13800138000", encoding="utf-8")
    code = run(["--path", str(tmp_path / "a.txt")])
    doc = json.loads(capsys.readouterr().out)
    assert code == 1
    assert doc["summary"]["scanned_ok"] == 1
    assert doc["findings"][0]["source"] == "a.txt"


def test_disable_all_is_usage_error():
    assert run(["--text", "x", "--disable", "cn_id,bank_card,phone,email"]) == 2


def test_locale_does_not_disable_recognizers(capsys):
    code = run(["--text", "id 11010519491231002X", "--locale", "en"])
    doc = json.loads(capsys.readouterr().out)
    assert code == 1
    assert any(f["type"] == "cn_id" for f in doc["findings"])


def test_determinism_json(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("id 11010519491231002X phone 13800138000", encoding="utf-8")
    o1, o2 = tmp_path / "o1.json", tmp_path / "o2.json"
    run(["--path", str(src), "-o", str(o1)])
    run(["--path", str(src), "-o", str(o2)])
    assert o1.read_bytes() == o2.read_bytes()


def test_sarif_structure(tmp_path, capsys):
    src = tmp_path / "a.txt"
    src.write_text("phone 13800138000", encoding="utf-8")
    run(["--path", str(src), "--format", "sarif"])
    doc = json.loads(capsys.readouterr().out)
    assert doc["version"] == "2.1.0"
    run0 = doc["runs"][0]
    assert run0["columnKind"] == "unicodeCodePoints"
    assert "startTime" not in run0 and "securityScore" not in run0
    region = run0["results"][0]["locations"][0]["physicalLocation"]["region"]
    assert region["endColumn"] == region["startColumn"] + 10  # phone length 11
