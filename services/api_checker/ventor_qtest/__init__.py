"""Vendored Ventor QTest integration.

The package is intentionally isolated from aig_api_checker's existing
algorithms so importing the original CLI and HTTP server keeps the same
runtime behavior.
"""

from .runner.cli import main

__all__ = ["main"]
