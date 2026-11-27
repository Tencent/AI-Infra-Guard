"""pii_scan - deterministic PII detection library.

Public API::

    from pii_scan import scan_text, scan_path
    findings = scan_text("call me 13800138000")
    findings, summary = scan_path("./data")
"""
from ._version import __version__
from .scanner import scan_text, scan_path

__all__ = ["scan_text", "scan_path", "__version__"]
