#!/usr/bin/env python3
"""Build and upload the independent AIG scanner packages.

Examples:
  python scripts/publish_pypi.py build
  python scripts/publish_pypi.py build infra --target all
  python scripts/publish_pypi.py upload mcp model
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Directory, distribution name, console script that must appear in the wheel.
MODULES: dict[str, tuple[str, str, str]] = {
    "skill": ("skill-scan", "aig-skill-scan", "aig-skill-scan"),
    "mcp": ("mcp-scan", "aig-mcp-scan", "aig-mcp-scan"),
    "agent": ("agent-scan", "aig-agent-scan", "aig-agent-scan"),
    "model": ("AIG-PromptSecurity", "aig-model-scan", "aig-model-scan"),
    "infra": ("infra-scan", "aig-infra-scan", "aig-infra-scan"),
}

# goos, goarch, wheel tag that replaces py3-none-any
TARGETS: dict[str, tuple[str, str, str]] = {
    "darwin/arm64": ("darwin", "arm64", "py3-none-macosx_11_0_arm64"),
    "darwin/amd64": ("darwin", "amd64", "py3-none-macosx_11_0_x86_64"),
    "linux/amd64": ("linux", "amd64", "py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64"),
    "linux/arm64": ("linux", "arm64", "py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64"),
    "windows/amd64": ("windows", "amd64", "py3-none-win_amd64"),
}

RULE_DIRS = ("fingerprints", "vuln", "vuln_en")


def host_target() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {
        "arm64": "arm64",
        "aarch64": "arm64",
        "x86_64": "amd64",
        "amd64": "amd64",
    }.get(machine)
    system = {"darwin": "darwin", "linux": "linux", "windows": "windows"}.get(system)
    key = f"{system}/{arch}"
    if key not in TARGETS:
        raise SystemExit(f"当前系统 {system}/{machine} 不在发布目标里")
    return key


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def record_hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).decode().rstrip("=")


def retag_wheel(path: Path, tag: str) -> Path:
    """Replace the generic py3-none-any tag so pip installs the bundled binary only on that OS."""
    if "py3-none-any" not in path.name:
        raise SystemExit(f"无法识别的 wheel 名称: {path.name}")
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        blobs = {info.filename: archive.read(info) for info in infos}
    wheel_name = next(name for name in blobs if name.endswith(".dist-info/WHEEL"))
    lines = []
    for line in blobs[wheel_name].decode().splitlines():
        lines.append(f"Tag: {tag}" if line.startswith("Tag:") else line)
    blobs[wheel_name] = ("\n".join(lines) + "\n").encode()
    record_name = next(name for name in blobs if name.endswith(".dist-info/RECORD"))
    rows = []
    for row in csv.reader(io.StringIO(blobs[record_name].decode())):
        if row and row[0] == wheel_name:
            data = blobs[wheel_name]
            row = [wheel_name, record_hash(data), str(len(data))]
        rows.append(row)
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    blobs[record_name] = buffer.getvalue().encode()
    dest = path.with_name(path.name.replace("py3-none-any", tag))
    with zipfile.ZipFile(dest, "w") as archive:
        for info in infos:
            archive.writestr(info, blobs[info.filename])
    path.unlink()
    return dest


def clear_dist(directory: Path) -> None:
    dist = directory / "dist"
    if dist.exists():
        shutil.rmtree(dist)


def build_python(directory: Path, clear: bool = True) -> list[Path]:
    if clear:
        clear_dist(directory)
    run([sys.executable, "-m", "build", "--wheel"], directory)
    wheels = sorted((directory / "dist").glob("*.whl"))
    if not wheels:
        raise SystemExit(f"{directory} 没有生成 wheel")
    return wheels


def assert_script(wheel: Path, script: str) -> None:
    with zipfile.ZipFile(wheel) as archive:
        entry = next(name for name in archive.namelist() if name.endswith(".dist-info/entry_points.txt"))
        text = archive.read(entry).decode()
    if f"{script} =" not in text:
        raise SystemExit(f"{wheel.name} 缺少命令 {script}")


def stage_infra(target: str) -> None:
    goos, goarch, _ = TARGETS[target]
    package = ROOT / "infra-scan" / "aig_infra_scan"
    binary_dir = package / "bin"
    data_dir = package / "data"
    binary_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    for name in RULE_DIRS:
        dest = data_dir / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(ROOT / "data" / name, dest, ignore=shutil.ignore_patterns(".DS_Store"))
    binary_name = "ai-infra-guard.exe" if goos == "windows" else "ai-infra-guard"
    for stale in binary_dir.iterdir():
        if stale.name != ".gitkeep":
            stale.unlink()
    env = os_environ()
    env["CGO_ENABLED"] = "0"
    env["GOOS"] = goos
    env["GOARCH"] = goarch
    output = binary_dir / binary_name
    run(
        [
            "go",
            "build",
            "-ldflags=-s -w",
            "-trimpath",
            "-buildvcs=false",
            "-o",
            str(output),
            "./cmd/cli/main.go",
        ],
        ROOT,
        env,
    )
    output.chmod(0o755)


def os_environ() -> dict[str, str]:
    import os

    return os.environ.copy()


def clean_infra_stage() -> None:
    package = ROOT / "infra-scan" / "aig_infra_scan"
    binary_dir = package / "bin"
    data_dir = package / "data"
    if binary_dir.exists():
        for path in binary_dir.iterdir():
            if path.name != ".gitkeep":
                path.unlink()
    if data_dir.exists():
        for path in data_dir.iterdir():
            if path.name == ".gitkeep":
                continue
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


def assert_infra_wheel(wheel: Path, target: str) -> None:
    goos = TARGETS[target][0]
    binary_name = "ai-infra-guard.exe" if goos == "windows" else "ai-infra-guard"
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    binaries = [name for name in names if "/bin/" in name and not name.endswith("/")]
    expected = [name for name in binaries if name.endswith(f"bin/{binary_name}")]
    if len(expected) != 1 or len(binaries) != 1:
        raise SystemExit(f"{wheel.name} 应只包含 {binary_name}，实际为 {binaries}")
    if not any("/data/fingerprints/" in name and name.endswith(".yaml") for name in names):
        raise SystemExit(f"{wheel.name} 没有打入指纹规则")
    if not any("/data/vuln/" in name and name.endswith(".yaml") for name in names):
        raise SystemExit(f"{wheel.name} 没有打入漏洞规则")


def build_infra(targets: list[str]) -> list[Path]:
    directory = ROOT / "infra-scan"
    clear_dist(directory)
    wheels: list[Path] = []
    try:
        for target in targets:
            print(f"== infra {target}", flush=True)
            stage_infra(target)
            # setuptools keeps files removed between builds, so a previous platform binary would be packed in too.
            for leftover in (directory / "build", directory / "aig_infra_scan.egg-info"):
                if leftover.exists():
                    shutil.rmtree(leftover)
            built = [path for path in build_python(directory, clear=False) if "py3-none-any" in path.name]
            if len(built) != 1:
                raise SystemExit(f"infra 一次构建应只有一个 wheel，实际 {len(built)}")
            wheels.append(retag_wheel(built[0], TARGETS[target][2]))
            assert_infra_wheel(wheels[-1], target)
            assert_script(wheels[-1], "aig-infra-scan")
    finally:
        clean_infra_stage()
    return wheels


def build_module(name: str, targets: list[str]) -> list[Path]:
    directory_name, _distribution, script = MODULES[name]
    if name == "infra":
        return build_infra(targets)
    wheels = build_python(ROOT / directory_name)
    for wheel in wheels:
        assert_script(wheel, script)
    return wheels


def upload(wheels: list[Path], repository: str) -> None:
    if not wheels:
        raise SystemExit("没有可上传的 wheel")
    run([sys.executable, "-m", "twine", "upload", "--repository", repository, *[str(path) for path in wheels]], ROOT)


def parse_targets(values: list[str]) -> list[str]:
    if not values:
        return [host_target()]
    if values == ["all"]:
        return list(TARGETS)
    unknown = [value for value in values if value not in TARGETS]
    if unknown:
        raise SystemExit(f"未知目标 {unknown}，可选: {', '.join(TARGETS)} 或 all")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="构建并上传各扫描模块的 PyPI 包")
    parser.add_argument("action", choices=("build", "upload"))
    parser.add_argument("modules", nargs="*", choices=list(MODULES))
    parser.add_argument("--target", action="append", default=[], help="infra 的系统/CPU，例如 darwin/arm64，或 all")
    parser.add_argument("--repository", default="pypi", help="twine 仓库名，默认 pypi，测试可用 testpypi")
    args = parser.parse_args()
    names = args.modules or list(MODULES)
    targets = parse_targets(args.target) if "infra" in names else []
    built: list[Path] = []
    for name in names:
        print(f"== {name}", flush=True)
        built.extend(build_module(name, targets if name == "infra" else []))
    for wheel in built:
        print(wheel)
    if args.action == "upload":
        upload(built, args.repository)


if __name__ == "__main__":
    main()
