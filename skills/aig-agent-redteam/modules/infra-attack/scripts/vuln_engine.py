"""Vulnerability engine: matches a (product, version) pair against CVE YAML rules.

Each CVE YAML has a `rule` field with a version-range expression like:
  version < "1.12.1"
  version >= "0.5.0" && version < "1.0.0"
  version <= "0.20.2"

This module evaluates that expression against the detected version.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class CVERule:
    file: Path
    product: str
    cve_id: str
    summary: str
    details: str
    severity: str
    cvss: str
    rule: str
    advice: str
    references: list = field(default_factory=list)


def _ver_tuple(v: str) -> tuple:
    """Convert "1.12.1" → (1, 12, 1) for comparison; missing parts default to 0.

    Tolerates trailing letters and dashes (1.0.0-beta, 1.0.0a) by stripping them.
    """
    if not v:
        return (0,)
    # Strip everything from first non-digit-or-dot
    m = re.match(r"^v?(\d+(?:\.\d+)*)", v.lower())
    if not m:
        return (0,)
    parts = m.group(1).split(".")
    return tuple(int(p) for p in parts)


def _ver_compare(v1: str, op: str, v2: str) -> bool:
    t1 = _ver_tuple(v1)
    t2 = _ver_tuple(v2)
    # Pad to same length
    L = max(len(t1), len(t2))
    t1 = t1 + (0,) * (L - len(t1))
    t2 = t2 + (0,) * (L - len(t2))
    if op == "<":
        return t1 < t2
    if op == "<=":
        return t1 <= t2
    if op == ">":
        return t1 > t2
    if op == ">=":
        return t1 >= t2
    if op == "==" or op == "=":
        return t1 == t2
    if op == "!=":
        return t1 != t2
    return False


_VER_RE = re.compile(r'version\s*(<=|>=|==|!=|<|>|=)\s*"([^"]+)"')


def _eval_rule(rule_expr: str, version: str) -> bool:
    """Eval rule like: version < "1.0" && version >= "0.5"."""
    if not rule_expr or not version:
        return False
    or_parts = re.split(r"\s*\|\|\s*", rule_expr)
    for or_part in or_parts:
        and_parts = re.split(r"\s*&&\s*", or_part)
        all_match = True
        for clause in and_parts:
            m = _VER_RE.search(clause.strip())
            if not m:
                all_match = False
                break
            op, target = m.group(1), m.group(2)
            if not _ver_compare(version, op, target):
                all_match = False
                break
        if all_match:
            return True
    return False


class VulnEngine:
    def __init__(self, vuln_dir: Path):
        self.vuln_dir = Path(vuln_dir)
        self.rules_by_product: dict[str, list[CVERule]] = {}
        if not self.vuln_dir.exists():
            # CVE 规则库未安装，Step C 静默跳过。
            # 下载方式：从 AI-Infra-Guard 仓库获取 data/vuln/ 放至此目录。
            return
        self._load()

    def _load(self):
        for product_dir in self.vuln_dir.iterdir():
            if not product_dir.is_dir():
                continue
            product_key = product_dir.name.lower()
            self.rules_by_product[product_key] = []
            for yf in product_dir.rglob("*.yaml"):
                try:
                    raw = yaml.safe_load(yf.read_text(encoding="utf-8"))
                    if not raw:
                        continue
                    info = raw.get("info") or {}
                    cve_id = info.get("cve") or info.get("ghsa") or yf.stem
                    self.rules_by_product[product_key].append(CVERule(
                        file=yf,
                        product=info.get("name", product_key),
                        cve_id=cve_id,
                        summary=info.get("summary", ""),
                        details=info.get("details", ""),
                        severity=(info.get("severity") or "INFO").upper(),
                        cvss=info.get("cvss", ""),
                        rule=raw.get("rule", ""),
                        advice=info.get("security_advise", ""),
                        references=info.get("references") or raw.get("references") or [],
                    ))
                except Exception as e:
                    print(f"warn: vuln parse {yf}: {e}", file=sys.stderr)

    def match(self, product: str, version: str) -> list[CVERule]:
        product_key = (product or "").lower()
        # Try exact match, then product folder name approximations
        if product_key in self.rules_by_product:
            rules = self.rules_by_product[product_key]
        else:
            # Fuzzy: find any product folder containing/matching the product name
            rules = []
            for k, v in self.rules_by_product.items():
                if k == product_key or k.replace("-", "") == product_key.replace("-", ""):
                    rules = v
                    break
            if not rules:
                # Also check by lowercased folder names
                for k, v in self.rules_by_product.items():
                    if product_key.startswith(k) or k.startswith(product_key):
                        rules = v
                        break

        if not rules:
            return []

        if not version:
            # Without version, return all CVEs for this product (info-level)
            return rules

        return [r for r in rules if _eval_rule(r.rule, version)]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--vuln-dir", default=str(Path(__file__).resolve().parent.parent / "data" / "vuln"))
    ap.add_argument("--product", required=True)
    ap.add_argument("--version", required=True)
    args = ap.parse_args()
    eng = VulnEngine(Path(args.vuln_dir))
    matches = eng.match(args.product, args.version)
    for m in matches:
        print(f"{m.severity:8} {m.cve_id:25} {m.summary[:80]}")
    print(f"\n→ {len(matches)} CVE(s) match {args.product}@{args.version}")
