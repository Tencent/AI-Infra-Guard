"""Config-file channel: hide the payload inside configuration files.

Agents that audit, review, or deploy applications read YAML, TOML, and
.env configuration files. A payload planted in a config value or comment
is ingested verbatim — and because config files are trusted by
convention, the model may be especially susceptible.
"""

from __future__ import annotations

from ..base import Channel
from . import register


@register("config_file")
class ConfigFileChannel(Channel):
    """Embed the payload in a configuration file.

    Parameters
    ----------
    fmt:
        * ``"yaml"`` (default) — ``key: value`` lines.
        * ``"toml"`` — ``key = "value"`` lines.
        * ``"env"`` — ``KEY=value`` lines.
    method:
        * ``"value"`` — appended to an existing config value.
        * ``"comment"`` — a comment line (``# payload``).
        * ``"new_key"`` — a new config key whose value is the payload.
    """

    def __init__(self, fmt: str = "yaml", method: str = "value") -> None:
        if fmt not in ("yaml", "toml", "env"):
            raise ValueError("fmt must be 'yaml', 'toml', or 'env'")
        if method not in ("value", "comment", "new_key"):
            raise ValueError("method must be 'value', 'comment', or 'new_key'")
        self.fmt = fmt
        self.method = method

    def _comment_prefix(self) -> str:
        return "#"

    def _taint_value(self, data: str, payload: str) -> str:
        lines = data.splitlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Modify the first non-comment line that looks like a setting.
            if self.fmt == "toml":
                if "=" in stripped:
                    # Append payload inside the quoted value.
                    val_start = stripped.index("=") + 1
                    prefix = stripped[:val_start]
                    rest = stripped[val_start:].strip()
                    if rest.startswith('"'):
                        # Insert before closing quote.
                        inner = rest.strip('"')
                        lines[i] = f'{prefix} "{inner} {payload}"'
                    else:
                        lines[i] = f'{prefix} {rest} {payload}'
                    return "\n".join(lines)
            elif self.fmt == "env":
                if "=" in stripped:
                    key, _, val = stripped.partition("=")
                    lines[i] = f"{key}={val} {payload}"
                    return "\n".join(lines)
            else:  # yaml
                if ":" in stripped:
                    key, _, val = stripped.partition(":")
                    lines[i] = f"{key}: {val} {payload}"
                    return "\n".join(lines)
        # No setting found — add one.
        if self.fmt == "toml":
            lines.append(f'extra = "{payload}"')
        elif self.fmt == "env":
            lines.append(f"EXTRA={payload}")
        else:
            lines.append(f"extra: {payload}")
        return "\n".join(lines)

    def _taint_comment(self, data: str, payload: str) -> str:
        one_line = " ".join(payload.splitlines())
        return f"{data}\n# {one_line}" if data else f"# {one_line}"

    def _taint_new_key(self, data: str, payload: str) -> str:
        one_line = " ".join(payload.splitlines())
        if self.fmt == "toml":
            return f'{data}\nextra_config = "{one_line}"' if data else f'extra_config = "{one_line}"'
        if self.fmt == "env":
            return f"{data}\nEXTRA_CONFIG={one_line}" if data else f"EXTRA_CONFIG={one_line}"
        return f"{data}\nextra_config: {one_line}" if data else f"extra_config: {one_line}"

    def taint(self, data: str, payload: str) -> str:
        if self.method == "comment":
            return self._taint_comment(data, payload)
        if self.method == "new_key":
            return self._taint_new_key(data, payload)
        return self._taint_value(data, payload)
