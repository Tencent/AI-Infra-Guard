#!/usr/bin/env python3
"""Compatibility shim.

The Go backend (common/agent) invokes scanners with
``uv run --no-project main.py`` from inside the scanner directory, so this
top-level shim must exist. Keep it in sync with the other scanners
(mcp-scan/main.py, skill-scan/main.py). The real entry point is
``pii_scan.main:cli``.
"""
from pii_scan.main import cli

if __name__ == "__main__":
    cli()
