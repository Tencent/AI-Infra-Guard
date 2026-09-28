"""Standard benchmark datasets for prompt-injection evaluation.

This module provides a thin loader layer that reads TOML test-case files
from the ``datasets/`` directory, converts each case into an
:class:`~pikit.config.ExperimentConfig`, and runs it through the existing
:class:`~pikit.matrix.MatrixRunner` — so dataset evaluation reuses the
exact same engine as custom matrix experiments.

Two built-in datasets ship with pikit:

* **direct_injection** — attacker payload delivered via the user message
  (``datasets/direct_injection.toml``).
* **indirect_injection** — attacker payload hidden in tool-returned data
  (``datasets/indirect_injection.toml``).

Each TOML file has a ``[meta]`` section and an array of ``[[cases]]``.
Every case is a flat dict whose keys map directly to ``ExperimentConfig``
fields, plus an ``id`` and ``description`` for reference.

Example
-------
>>> from pikit.datasets import list_datasets, load_dataset, run_dataset
>>> list_datasets()
['direct_injection', 'indirect_injection']
>>> results = run_dataset("direct_injection", target_spec="mock")
>>> len(results) > 0
True
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..config import ExperimentConfig
from ..matrix import ExperimentResult, MatrixRunner, save_json, save_csv

_DATASETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "datasets")


@dataclass
class DatasetCase:
    """One test case from a dataset TOML file.

    Attributes
    ----------
    id:
        Short identifier (e.g. ``"di-001"``).
    description:
        Human-readable description of what the case tests.
    config:
        A fully-built :class:`ExperimentConfig` ready to run.
    """

    id: str
    description: str
    config: ExperimentConfig


@dataclass
class Dataset:
    """A loaded benchmark dataset.

    Attributes
    ----------
    name:
        Dataset name from the ``[meta]`` section.
    description:
        Dataset description from ``[meta]``.
    reference:
        Academic reference string from ``[meta]``.
    cases:
        List of :class:`DatasetCase` objects.
    path:
        Filesystem path to the source TOML file.
    """

    name: str
    description: str
    reference: str
    cases: List[DatasetCase] = field(default_factory=list)
    path: str = ""


def _find_toml_files() -> List[str]:
    """Return sorted paths to all ``.toml`` files in the datasets directory."""
    files = []
    for fname in sorted(os.listdir(_DATASETS_DIR)):
        if fname.endswith(".toml"):
            files.append(os.path.join(_DATASETS_DIR, fname))
    return files


def list_datasets() -> List[str]:
    """Return the names of all available built-in datasets.

    Examples
    --------
    >>> list_datasets()
    ['direct_injection', 'indirect_injection']
    """
    names = []
    for path in _find_toml_files():
        from pikit._compat import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)
        meta = data.get("meta", {})
        names.append(meta.get("name", os.path.splitext(os.path.basename(path))[0]))
    return names


def load_dataset(name: str) -> Dataset:
    """Load a built-in dataset by name.

    Parameters
    ----------
    name:
        Dataset name (e.g. ``"direct_injection"``).

    Returns
    -------
    Dataset
        The loaded dataset with all cases parsed.

    Raises
    ------
    KeyError
        If no dataset with that name exists.
    """
    from pikit._compat import tomllib

    for path in _find_toml_files():
        with open(path, "rb") as f:
            data = tomllib.load(f)
        meta = data.get("meta", {})
        ds_name = meta.get("name", os.path.splitext(os.path.basename(path))[0])
        if ds_name == name:
            cases = []
            for raw in data.get("cases", []):
                # Never mutate parsed TOML data in place: callers may load a
                # dataset repeatedly in the same process.
                case_data = dict(raw)
                case_id = case_data.pop("id", f"case-{len(cases)+1:03d}")
                case_desc = case_data.pop("description", "")
                cfg = ExperimentConfig.from_dict(case_data)
                cases.append(DatasetCase(id=case_id, description=case_desc, config=cfg))
            return Dataset(
                name=ds_name,
                description=meta.get("description", ""),
                reference=meta.get("reference", ""),
                cases=cases,
                path=path,
            )

    available = list_datasets()
    raise KeyError(f"Dataset '{name}' not found. Available: {available}")


def run_dataset(
    name: str,
    *,
    target_spec: Optional[str] = None,
    judge_type: Optional[str] = None,
    temperature: Optional[float] = None,
    repeats: Optional[int] = None,
    attacks: Optional[List[str]] = None,
    verbose: bool = False,
) -> List[ExperimentResult]:
    """Run all cases in a dataset and collect results.

    Each case is run independently via :class:`MatrixRunner`.  Results from
    all cases are concatenated into a single list, with the ``case_id`` and
    ``case_description`` stored in each result's ``reason`` prefix for
    traceability.

    Parameters
    ----------
    name:
        Dataset name.
    target_spec:
        Override the target spec for all cases (e.g. ``"openai:gpt-4o-mini"``).
        Defaults to each case's own spec (usually ``"mock"``).
    judge_type:
        Override the judge type for all cases.
    temperature:
        Override sampling temperature.
    repeats:
        Override number of repeats per case.
    attacks:
        Override the attack methods for all cases (e.g. ``["naive", "escape"]``).
        When provided, every case will use these attacks regardless of what
        the dataset TOML specifies (or omits).  When ``None``, each case falls
        back to its own ``attacks`` field, or ``["naive"]`` if
        the dataset omits the field entirely (naive = raw payload without
        any attack-method wrapping).
    verbose:
        Print progress to stderr.

    Returns
    -------
    List[ExperimentResult]
        Results from all cases, in dataset order.
    """
    ds = load_dataset(name)
    all_results: List[ExperimentResult] = []

    for i, case in enumerate(ds.cases, 1):
        cfg = case.config
        # Apply overrides.
        if target_spec is not None:
            cfg.target_spec = target_spec
        if judge_type is not None:
            cfg.judge_type = judge_type
        if temperature is not None:
            cfg.temperature = temperature
        if repeats is not None:
            cfg.repeats = repeats
        if attacks is not None:
            cfg.attacks = list(attacks)

        if verbose:
            import sys
            print(f"[{i}/{len(ds.cases)}] {case.id}: {case.description}", file=sys.stderr)

        runner = MatrixRunner(cfg, verbose=verbose)
        results = runner.run()
        # Tag each result with the case id for traceability.
        for r in results:
            r.case_id = case.id
            r.metadata["case_description"] = case.description
        all_results.extend(results)

    return all_results


__all__ = [
    "DatasetCase",
    "Dataset",
    "list_datasets",
    "load_dataset",
    "run_dataset",
]
