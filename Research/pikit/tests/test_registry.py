"""Tests for the registry and the target factory."""

import pytest

from pikit import attacks, defenses, get_target
from pikit.registry import Registry


def test_expected_attacks_registered():
    for key in [
        "naive",
        "escape",
        "context_ignoring",
        "fake_completion",
        "combined",
        "payload_splitting",
        "obfuscation",
        "prefix_injection",
        "format_confusion",
        "context_flooding",
        "cross_channel",
        "important_instructions",
        "stealth_instruction",
    ]:
        assert key in attacks.list()
        assert attacks.get(key)().name == key


def test_expected_defenses_registered():
    for key in [
        "delimiters",
        "sandwich",
        "instructional",
        "spotlighting",
        "random_sequence_enclosure",
        "retokenization",
    ]:
        assert key in defenses.list()
        assert defenses.get(key)().name == key


def test_get_unknown_attack_raises_with_available():
    with pytest.raises(KeyError) as exc:
        attacks.get("does_not_exist")
    assert "available" in str(exc.value)


def test_duplicate_registration_raises():
    reg = Registry("attack")

    @reg.register("dup")
    class _A:
        pass

    with pytest.raises(ValueError):

        @reg.register("dup")
        class _B:
            pass


def test_registry_sets_name_attribute():
    reg = Registry("attack")

    @reg.register("foo")
    class _A:  # no own `name` -> registry assigns the key
        pass

    assert _A.name == "foo"


def test_registry_keeps_explicit_name():
    reg = Registry("attack")

    @reg.register("foo")
    class _A:
        name = "custom"  # explicitly declared -> preserved

    assert _A.name == "custom"


def test_get_target_mock_and_unknown():
    tgt = get_target("mock")
    assert tgt.query("hi").endswith("hi")
    with pytest.raises(ValueError):
        get_target("bogus:model")
