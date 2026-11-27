from pii_scan.utils.bin_prefix import card_bin_known
from pii_scan.utils.gb11643 import cn_id_valid
from pii_scan.utils.luhn import luhn_valid


def test_luhn_valid_and_invalid():
    assert luhn_valid("4532015112830366")
    assert luhn_valid("4111111111111111")
    assert not luhn_valid("4532015112830367")
    assert not luhn_valid("0000")


def test_cn_id_checksum_and_date():
    assert cn_id_valid("11010519491231002X")
    assert cn_id_valid("11010519491231002x")          # case-insensitive check digit
    assert not cn_id_valid("110105194912310021")      # wrong check digit
    assert not cn_id_valid("11010519491330002X")      # invalid month 13
    assert not cn_id_valid("11010519491231002X0")     # wrong length


def test_card_bin_whitelist():
    assert card_bin_known("4111111111111111")          # Visa
    assert card_bin_known("5555555555554444")          # Mastercard 51-55
    assert card_bin_known("6011000990139424")          # Discover 6011
    assert not card_bin_known("0000000000000000")      # no known issuer
