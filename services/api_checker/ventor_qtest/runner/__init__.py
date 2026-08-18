"""Runner package providing orchestrated execution and CLI utilities."""

from __future__ import annotations

from typing import Any, List


def run_tests(config: Any) -> List[str]:
    """Lazy import wrapper to avoid heavy side effects during package import."""

    from .orchestrator import run_tests as _run_tests

    return _run_tests(config)


__all__ = ["run_tests"]
