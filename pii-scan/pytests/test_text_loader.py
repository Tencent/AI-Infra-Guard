from pii_scan.utils.text_loader import decode_bytes, is_binary


def test_decode_utf8():
    assert decode_bytes("中文".encode("utf-8"))[0] == "中文"


def test_decode_gb18030():
    assert decode_bytes("中文".encode("gb18030"))[0] == "中文"


def test_binary_detected():
    assert is_binary(b"\x00\x01\x02\x03")
    assert not is_binary("hello world".encode("utf-8"))
