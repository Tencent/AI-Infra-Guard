"""Run the bundled Go scanner with the fingerprint and advisory rules shipped in this package."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class InfraScanError(RuntimeError):
    """The bundled scanner could not run or did not return JSON."""


def binary_path() -> Path:
    name = "ai-infra-guard.exe" if os.name == "nt" else "ai-infra-guard"
    path = ROOT / "bin" / name
    if not path.is_file():
        raise InfraScanError(
            "aig-infra-scan 安装包里没有当前系统的扫描程序。"
            "请安装与本机系统匹配的 wheel，或在仓库中执行 "
            "python scripts/publish_pypi.py build infra"
        )
    return path


def rules_dir(name: str) -> Path:
    packaged = ROOT / "data" / name
    if packaged.is_dir() and any(packaged.rglob("*.y*ml")):
        return packaged
    # Editable installs keep the rules in the repository data directory.
    repo = ROOT.parents[1] / "data" / name
    if repo.is_dir():
        return repo
    raise InfraScanError(f"aig-infra-scan 安装包里没有规则目录 {name}")


def scan_argv(argv: list[str]) -> list[str]:
    """Fill the default rule paths when the caller did not pass them."""
    extra: list[str] = []
    if "--fps" not in argv:
        extra.extend(["--fps", str(rules_dir("fingerprints"))])
    if "--vul" not in argv:
        extra.extend(["--vul", str(rules_dir("vuln"))])
    return extra + argv


def scan(target: str, lang: str = "zh") -> list:
    """Scan one target and return the JSON result. Does not replace the current process."""
    binary = binary_path()
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "result.json"
        argv = scan_argv(["-t", target, "--json", "-o", str(output), "--lang", lang])
        try:
            completed = subprocess.run(
                [str(binary), "scan", *argv],
                check=False,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise InfraScanError("基础设施扫描失败") from exc
        if completed.returncode != 0 or not output.is_file():
            raise InfraScanError("基础设施扫描失败")
        try:
            payload = json.loads(output.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise InfraScanError("基础设施扫描结果无法解析") from exc
    if isinstance(payload, list):
        return payload
    return [payload]


def main() -> None:
    try:
        binary = binary_path()
        argv = scan_argv(sys.argv[1:])
    except InfraScanError as exc:
        raise SystemExit(str(exc)) from exc
    os.execv(str(binary), [str(binary), "scan", *argv])
