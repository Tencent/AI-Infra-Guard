from pii_scan.recognizers import bank_card, cn_id, email, phone


def _vals(module, text):
    return [h.value for h in module.recognize(text)]


def test_email():
    assert _vals(email, "a@b.com") == ["a@b.com"]
    assert _vals(email, "no address here") == []


def test_phone_boundary():
    assert _vals(phone, "13800138000") == ["13800138000"]
    assert _vals(phone, "abc13800138000def") == ["13800138000"]
    assert _vals(phone, "1380013800012") == []       # 13 digits, embedded


def test_cn_id():
    assert _vals(cn_id, "11010519491231002X") == ["11010519491231002X"]
    assert _vals(cn_id, "110105194912310021") == []  # bad check digit


def test_bank_card_confidence_and_luhn():
    high = [(h.value, h.confidence) for h in bank_card.recognize("4111111111111111")]
    assert high and high[0][1] == "high"
    low = [(h.value, h.confidence) for h in bank_card.recognize("0000000000000000")]
    assert low and low[0][1] == "low"                # Luhn ok, unknown BIN
    assert _vals(bank_card, "4111111111111112") == []  # Luhn fail
