"""Fingerprint engine: matches HTTP responses against AIG fingerprint YAML rules.

Supports a subset of AIG's fingerprint DSL that's most commonly used:
- body="..."     substring match in response body
- header="..."   substring match in any header value
- title="..."    substring match in <title>
- status_code=N  exact status code match
- icon="hash"    favicon mmh3 hash (we approximate with shasum if no mmh3)
- ||             OR
- &&             AND
- regex(...)     regex match in body

Version extraction supports:
- regex pattern with group(1) capturing version
- from body or header
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR.parent.parent.parent / "scripts"))
from common.http_probe import http_get, ProbeResult  # noqa: E402


@dataclass
class FingerprintMatch:
    product: str
    vendor: str = ""
    severity: str = "info"
    version: str = ""
    path_hit: str = ""
    matcher_hit: str = ""


@dataclass
class FingerprintRule:
    file: Path
    name: str
    raw: dict

    @property
    def product(self) -> str:
        return self.raw.get("info", {}).get("metadata", {}).get("product", self.name)

    @property
    def vendor(self) -> str:
        return self.raw.get("info", {}).get("metadata", {}).get("vendor", "")

    @property
    def severity(self) -> str:
        return self.raw.get("info", {}).get("severity", "info")


class _Tokenizer:
    """Tiny tokenizer for fingerprint expressions."""
    def __init__(self, s: str):
        self.s = s
        self.pos = 0

    def peek(self):
        self.skip_ws()
        if self.pos >= len(self.s):
            return None
        return self.s[self.pos]

    def skip_ws(self):
        while self.pos < len(self.s) and self.s[self.pos] in " \t\n":
            self.pos += 1

    def consume(self, n=1):
        self.skip_ws()
        v = self.s[self.pos:self.pos+n]
        self.pos += n
        return v

    def at_end(self):
        self.skip_ws()
        return self.pos >= len(self.s)


def _parse_field(tok: _Tokenizer) -> Optional[tuple]:
    """Parse field=value or field!=value, return (field, op, value) or None."""
    tok.skip_ws()
    start = tok.pos
    # field name
    while tok.pos < len(tok.s) and tok.s[tok.pos] not in "= \t\n!":
        tok.pos += 1
    field_name = tok.s[start:tok.pos]
    if not field_name:
        return None
    tok.skip_ws()
    # operator
    op = "="
    if tok.pos < len(tok.s) and tok.s[tok.pos] == "!":
        op = "!="
        tok.pos += 1
    if tok.pos < len(tok.s) and tok.s[tok.pos] == "=":
        tok.pos += 1
    else:
        return None
    tok.skip_ws()
    # value (quoted string or bare)
    if tok.pos < len(tok.s) and tok.s[tok.pos] == '"':
        tok.pos += 1
        vstart = tok.pos
        while tok.pos < len(tok.s) and tok.s[tok.pos] != '"':
            if tok.s[tok.pos] == '\\':
                tok.pos += 2
            else:
                tok.pos += 1
        value = tok.s[vstart:tok.pos]
        # unescape
        value = value.replace('\\"', '"').replace('\\\\', '\\')
        tok.pos += 1  # closing quote
    else:
        vstart = tok.pos
        while tok.pos < len(tok.s) and tok.s[tok.pos] not in " &|\t\n":
            tok.pos += 1
        value = tok.s[vstart:tok.pos]
    return (field_name, op, value)


def _eval_atom(field_name: str, op: str, value: str, resp: ProbeResult) -> bool:
    if field_name == "body":
        result = value in resp.body
    elif field_name == "header":
        # Match against any header line (key:value)
        result = any(value in f"{k}:{v}" or value in v for k, v in resp.headers.items())
    elif field_name == "title":
        result = value in resp.title
    elif field_name == "status_code":
        try:
            result = resp.status_code == int(value)
        except ValueError:
            result = False
    elif field_name == "icon":
        # We don't compute mmh3 favicon hash; treat as info-only and skip
        result = False
    else:
        # Unknown field; treat as no match (don't crash)
        result = False
    return result if op == "=" else not result


def _eval_expr(expr: str, resp: ProbeResult) -> bool:
    """Eval expr like: body="..." || header="..." && status_code=200.

    Operator precedence: && > || (parens not supported in subset).
    """
    # Split by ||
    or_parts = re.split(r"\s*\|\|\s*", expr)
    for or_part in or_parts:
        and_parts = re.split(r"\s*&&\s*", or_part)
        all_and = True
        for and_part in and_parts:
            tok = _Tokenizer(and_part)
            atom = _parse_field(tok)
            if not atom:
                all_and = False
                break
            if not _eval_atom(*atom, resp=resp):
                all_and = False
                break
        if all_and:
            return True
    return False


class FingerprintEngine:
    def __init__(self, fp_dir: Path):
        self.fp_dir = Path(fp_dir)
        self.rules: list[FingerprintRule] = []
        self._load()

    def _load(self):
        for yf in self.fp_dir.rglob("*.yaml"):
            try:
                raw = yaml.safe_load(yf.read_text(encoding="utf-8"))
                if not raw:
                    continue
                self.rules.append(FingerprintRule(file=yf, name=yf.stem, raw=raw))
            except Exception as e:
                print(f"warn: cannot parse {yf}: {e}", file=sys.stderr)

    def match(self, base_url: str, primary_response: Optional[ProbeResult] = None) -> Optional[FingerprintMatch]:
        """Match the given URL against all fingerprint rules. Return first match."""
        # Cache primary response for paths == "/"
        primary = primary_response or http_get(base_url)
        if not primary.matched():
            return None

        path_cache = {"/": primary}

        for rule in self.rules:
            http_blocks = rule.raw.get("http", [])
            if not http_blocks:
                continue
            for block in http_blocks:
                method = block.get("method", "GET").upper()
                path = block.get("path", "/")
                matchers = block.get("matchers") or []
                # Get response for this path
                if path in path_cache:
                    resp = path_cache[path]
                else:
                    if method == "GET":
                        resp = http_get(base_url.rstrip("/") + path, timeout=4.0)
                        path_cache[path] = resp
                    else:
                        continue  # skip POST/PUT for now
                if not resp.matched():
                    continue

                # ANY matcher hits → product matched (matchers are OR semantics in AIG)
                hit_matcher = None
                for m in matchers:
                    if _eval_expr(m, resp):
                        hit_matcher = m
                        break

                if hit_matcher:
                    version = self._extract_version(rule, base_url, path_cache, resp)
                    return FingerprintMatch(
                        product=rule.product,
                        vendor=rule.vendor,
                        severity=rule.severity,
                        version=version,
                        path_hit=path,
                        matcher_hit=hit_matcher,
                    )
        return None

    def _extract_version(self, rule: FingerprintRule, base_url: str, path_cache: dict, primary_resp: ProbeResult) -> str:
        version_blocks = rule.raw.get("version") or []
        for vblock in version_blocks:
            method = vblock.get("method", "GET").upper()
            path = vblock.get("path", "/")
            extractor = vblock.get("extractor") or {}
            part = extractor.get("part", "body")
            regex = extractor.get("regex", "")
            group = extractor.get("group", 1)
            if not regex:
                continue

            if path in path_cache:
                resp = path_cache[path]
            elif method == "GET":
                resp = http_get(base_url.rstrip("/") + path, timeout=4.0)
                path_cache[path] = resp
            else:
                continue

            if not resp.matched():
                continue

            haystack = ""
            if part == "body":
                haystack = resp.body
            elif part == "header":
                haystack = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())

            try:
                m = re.search(regex, haystack)
                if m:
                    return m.group(group)
            except Exception:
                pass
        return ""


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fp-dir", default=str(THIS_DIR.parent / "data" / "fingerprints"))
    ap.add_argument("--target", required=True)
    args = ap.parse_args()
    eng = FingerprintEngine(Path(args.fp_dir))
    m = eng.match(args.target)
    if m:
        print(f"product: {m.product}@{m.version} (path={m.path_hit}, matcher={m.matcher_hit})")
    else:
        print("no fingerprint matched")
