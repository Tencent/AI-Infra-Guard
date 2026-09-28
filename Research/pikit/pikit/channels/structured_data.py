"""Structured-data channel: hide the payload inside JSON / CSV / TSV.

Agents that query APIs, databases, or spreadsheets ingest structured
responses. A payload planted in a field value, a column name, or a
comment line blends in naturally and is processed verbatim by the model.
"""

from __future__ import annotations

import json as _json

from ..base import Channel
from . import register


@register("structured_data")
class StructuredDataChannel(Channel):
    """Embed the payload in a JSON / CSV / TSV data artifact.

    Parameters
    ----------
    fmt:
        ``"json"`` (default), ``"csv"``, or ``"tsv"``.
    method:
        * ``"field_value"`` — inside a data field value.
        * ``"field_name"`` — as a new key / column header.
        * ``"comment"`` — a comment-style line (CSV/TSV ``# payload``;
          JSON ``"_comment"`` key).
    """

    def __init__(self, fmt: str = "json", method: str = "field_value") -> None:
        if fmt not in ("json", "csv", "tsv"):
            raise ValueError("fmt must be 'json', 'csv', or 'tsv'")
        if method not in ("field_value", "field_name", "comment"):
            raise ValueError(
                "method must be 'field_value', 'field_name', or 'comment'"
            )
        self.fmt = fmt
        self.method = method

    def _taint_json(self, data: str, payload: str) -> str:
        if self.method == "comment":
            try:
                obj = _json.loads(data)
            except _json.JSONDecodeError:
                obj = {}
            if isinstance(obj, dict):
                obj["_comment"] = payload
            elif isinstance(obj, list):
                obj.append({"_comment": payload})
            else:
                obj = {"_value": obj, "_comment": payload}
            return _json.dumps(obj, indent=2, ensure_ascii=False)

        if self.method == "field_name":
            try:
                obj = _json.loads(data)
            except _json.JSONDecodeError:
                obj = {}
            if isinstance(obj, dict):
                obj[payload] = "n/a"
            elif isinstance(obj, list):
                obj.append({payload: "n/a"})
            else:
                obj = {"_value": obj, payload: "n/a"}
            return _json.dumps(obj, indent=2, ensure_ascii=False)

        # field_value
        try:
            obj = _json.loads(data)
        except _json.JSONDecodeError:
            obj = {"data": data}
        if isinstance(obj, dict):
            # Append payload to the first string value, or add a new field.
            injected = False
            for k, v in list(obj.items()):
                if isinstance(v, str):
                    obj[k] = f"{v} {payload}"
                    injected = True
                    break
            if not injected:
                obj["_note"] = payload
        elif isinstance(obj, list):
            obj.append(payload)
        else:
            obj = {"_value": obj, "_note": payload}
        return _json.dumps(obj, indent=2, ensure_ascii=False)

    def _taint_delimited(self, data: str, payload: str, sep: str) -> str:
        lines = data.splitlines()
        if not lines:
            lines = [""]

        if self.method == "comment":
            return f"{lines[0]}\n# {payload}\n" + "\n".join(lines[1:])

        if self.method == "field_name":
            header = lines[0].split(sep)
            header.append(payload)
            lines[0] = sep.join(header)
            # Add a value row for the new column.
            for i in range(1, len(lines)):
                parts = lines[i].split(sep)
                parts.append("n/a")
                lines[i] = sep.join(parts)
            return "\n".join(lines)

        # field_value: append payload to the last cell of the first data row.
        if len(lines) > 1:
            parts = lines[1].split(sep)
            parts[-1] = f"{parts[-1]} {payload}"
            lines[1] = sep.join(parts)
        else:
            lines[0] = f"{lines[0]}{sep}{payload}"
        return "\n".join(lines)

    def taint(self, data: str, payload: str) -> str:
        if self.fmt == "json":
            return self._taint_json(data, payload)
        sep = "," if self.fmt == "csv" else "\t"
        return self._taint_delimited(data, payload, sep)

    def taint_file(self, path: str, payload: str, output_path=None) -> str:
        """Inject the payload into a real structured-data file.

        Detects the format from the file extension (``.json``, ``.csv``,
        ``.tsv``) and injects accordingly, writing a valid tainted file.
        """
        import os

        ext = os.path.splitext(path)[1].lower()
        # Map extension to format, overriding the instance default.
        if ext == ".json":
            old_fmt = self.fmt
            self.fmt = "json"
            try:
                result = super().taint_file(path, payload, output_path)
            finally:
                self.fmt = old_fmt
            return result
        elif ext == ".csv":
            old_fmt = self.fmt
            self.fmt = "csv"
            try:
                result = super().taint_file(path, payload, output_path)
            finally:
                self.fmt = old_fmt
            return result
        elif ext == ".tsv":
            old_fmt = self.fmt
            self.fmt = "tsv"
            try:
                result = super().taint_file(path, payload, output_path)
            finally:
                self.fmt = old_fmt
            return result
        else:
            return super().taint_file(path, payload, output_path)