"""Run the bundled Go scanner with the fingerprint and advisory rules shipped in this package."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def binary_path() -> Path:
    name = "ai-infra-guard.exe" if os.name == "nt" else "ai-infra-guard"
    path = ROOT / "bin" / name
    if not path.is_file():
        raise SystemExit(
            "aig-infra-scan 安装包里没有当前系统的扫描程序。"
            "请安装与本机系统匹配的 wheel，或在仓库中执行 "
            "python scripts/publish_pypi.py build infra"
        )
    return path


def rules_dir(name: str) -> Path:
    path = ROOT / "data" / name
    if not path.is_dir():
        raise SystemExit(f"aig-infra-scan 安装包里没有规则目录 {name}")
    return path


def scan_argv(argv: list[str]) -> list[str]:
    """Fill the default rule paths when the caller did not pass them."""
    extra: list[str] = []
    if "--fps" not in argv:
        extra.extend(["--fps", str(rules_dir("fingerprints"))])
    if "--vul" not in argv:
        extra.extend(["--vul", str(rules_dir("vuln"))])
    return extra + argv


def main() -> None:
    binary = binary_path()
    argv = scan_argv(sys.argv[1:])
    os.execv(str(binary), [str(binary), "scan", *argv])
