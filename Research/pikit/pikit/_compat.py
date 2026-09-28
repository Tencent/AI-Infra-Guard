"""TOML loader compatibility shim.

``tomllib`` is part of the standard library since Python 3.11.  For older
Pythons (3.9 / 3.10) we fall back to the third-party ``tomli`` package,
which is API-compatible.

Usage::

    from pikit._compat import tomllib
    with open("config.toml", "rb") as f:
        data = tomllib.load(f)
"""

from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    import tomllib  # noqa: F401
else:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore  # noqa: F401
    except ImportError:
        raise ImportError(
            "On Python < 3.11, install the 'tomli' package: pip install tomli"
        )
