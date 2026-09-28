"""Bundled safe fixture-plugin source trees for external runtimes."""
from __future__ import annotations
from pathlib import Path

_ROOT = Path(__file__).parent

def fixture_path(runtime: str) -> str:
    """Return the packaged fixture source path for ``openclaw`` or ``hermes``."""
    names = {"openclaw": "openclaw_fixture", "hermes": "hermes_fixture"}
    try:
        return str(_ROOT / names[runtime])
    except KeyError as exc:
        raise ValueError("runtime must be 'openclaw' or 'hermes'") from exc

__all__ = ["fixture_path"]
