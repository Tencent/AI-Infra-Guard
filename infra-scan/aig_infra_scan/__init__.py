"""Python wrapper around the AI-Infra-Guard infrastructure scanner."""

from aig_infra_scan.cli import InfraScanError, scan

__version__ = "0.1.0"

__all__ = ["InfraScanError", "scan"]
