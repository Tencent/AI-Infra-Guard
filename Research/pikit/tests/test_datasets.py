"""Tests for the benchmark datasets module."""

import json
import os
import tempfile

from pikit.datasets import list_datasets, load_dataset, run_dataset


def test_list_datasets():
    """list_datasets should return both built-in datasets."""
    names = list_datasets()
    assert "direct_injection" in names
    assert "indirect_injection" in names


def test_load_direct_dataset():
    """load_dataset should parse the direct injection TOML correctly."""
    ds = load_dataset("direct_injection")
    assert ds.name == "direct_injection"
    assert len(ds.cases) >= 19
    # Each case should have an id and a config.
    for case in ds.cases:
        assert case.id.startswith("di-")
        assert case.description
        assert case.config is not None
    # First case should be chat agent, naive attack.
    assert ds.cases[0].config.agents == ["chat"]
    assert ds.cases[0].config.attacks == ["naive"]


def test_load_indirect_dataset():
    """load_dataset should parse the indirect injection TOML correctly."""
    ds = load_dataset("indirect_injection")
    assert ds.name == "indirect_injection"
    assert len(ds.cases) >= 19
    for case in ds.cases:
        assert case.id.startswith("ii-")
        assert case.description
    # First case should use browser agent + webpage channel.
    assert ds.cases[0].config.agents == ["browser"]
    assert ds.cases[0].config.channels == ["webpage"]


def test_dataset_has_sink_cases():
    """Both datasets should include sink-based judgement cases."""
    for name in ["direct_injection", "indirect_injection"]:
        ds = load_dataset(name)
        sink_cases = [c for c in ds.cases if c.config.require_sink]
        assert len(sink_cases) > 0, f"{name} should have at least one sink case"


def test_dataset_has_defense_cases():
    """Both datasets should include defense cases."""
    for name in ["direct_injection", "indirect_injection"]:
        ds = load_dataset(name)
        defense_cases = [c for c in ds.cases if c.config.defenses != ["none"]]
        assert len(defense_cases) > 0, f"{name} should have at least one defense case"


def test_run_direct_dataset_mock():
    """run_dataset should produce results for every case (mock target)."""
    results = run_dataset("direct_injection", target_spec="mock")
    # Each case produces at least 1 result.
    assert len(results) >= 19
    for r in results:
        assert r.attack  # should be populated
        assert r.case_id.startswith("di-")


def test_run_indirect_dataset_mock():
    """run_dataset should produce results for every case (mock target)."""
    results = run_dataset("indirect_injection", target_spec="mock")
    assert len(results) >= 19
    for r in results:
        assert r.case_id.startswith("ii-")


def test_run_dataset_with_overrides():
    """Overrides should take effect across all cases."""
    results = run_dataset(
        "direct_injection",
        target_spec="mock",
        temperature=0.5,
        repeats=2,
    )
    # With repeats=2, each case produces 2 individual + 1 summary = 3.
    ds = load_dataset("direct_injection")
    expected = len(ds.cases) * 3
    assert len(results) == expected


def test_load_nonexistent_dataset():
    """Loading an unknown dataset should raise KeyError."""
    try:
        load_dataset("nonexistent")
        assert False, "Should have raised KeyError"
    except KeyError:
        pass


def test_dataset_case_ids_unique():
    """All case ids within a dataset should be unique."""
    for name in ["direct_injection", "indirect_injection"]:
        ds = load_dataset(name)
        ids = [c.id for c in ds.cases]
        assert len(ids) == len(set(ids)), f"Duplicate ids in {name}"
