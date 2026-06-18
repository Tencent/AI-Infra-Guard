#!/usr/bin/env python3
"""AI-Infra-Guard data resolver.

只复用 Tencent AI-Infra-Guard 的 data/ 目录，不导入其扫描器执行逻辑。
优先使用本地 AIG_DATA_DIR/AIG_ROOT；必要时可下载 AIG 到临时目录后使用 data/。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


AIG_REPO = "https://github.com/tencent/AI-Infra-Guard.git"
DEFAULT_LOCAL_ROOTS = [
    Path("/Users/python/Downloads/sec-page/AI-Infra-Guard"),
    Path.cwd().parent / "AI-Infra-Guard",
]


@dataclass
class AIGData:
    data_dir: Path
    source: str
    root_dir: Path | None = None

    @property
    def fingerprints_dir(self) -> Path:
        return self.data_dir / "fingerprints"

    @property
    def vuln_dir(self) -> Path:
        return self.data_dir / "vuln"

    @property
    def vuln_en_dir(self) -> Path:
        return self.data_dir / "vuln_en"

    @property
    def eval_dir(self) -> Path:
        return self.data_dir / "eval"

    @property
    def mcp_dir(self) -> Path:
        return self.data_dir / "mcp"

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "root_dir": str(self.root_dir) if self.root_dir else None,
            "data_dir": str(self.data_dir),
            "fingerprints_dir": str(self.fingerprints_dir),
            "vuln_dir": str(self.vuln_dir),
            "vuln_en_dir": str(self.vuln_en_dir),
            "eval_dir": str(self.eval_dir),
            "mcp_dir": str(self.mcp_dir),
            "exists": {
                "data": self.data_dir.exists(),
                "fingerprints": self.fingerprints_dir.exists(),
                "vuln": self.vuln_dir.exists(),
                "vuln_en": self.vuln_en_dir.exists(),
                "eval": self.eval_dir.exists(),
                "mcp": self.mcp_dir.exists(),
            },
            "counts": count_data_files(self.data_dir),
        }


def count_data_files(data_dir: Path) -> dict:
    if not data_dir.exists():
        return {}
    return {
        "fingerprints_yaml": len(list((data_dir / "fingerprints").rglob("*.yaml"))) if (data_dir / "fingerprints").exists() else 0,
        "vuln_yaml": len(list((data_dir / "vuln").rglob("*.yaml"))) if (data_dir / "vuln").exists() else 0,
        "vuln_en_yaml": len(list((data_dir / "vuln_en").rglob("*.yaml"))) if (data_dir / "vuln_en").exists() else 0,
        "eval_json": len(list((data_dir / "eval").rglob("*.json"))) if (data_dir / "eval").exists() else 0,
        "mcp_yaml": len(list((data_dir / "mcp").rglob("*.yaml"))) if (data_dir / "mcp").exists() else 0,
    }


def _as_data_dir(path: Path) -> Path | None:
    path = path.expanduser().resolve()
    if (path / "fingerprints").exists() or (path / "vuln").exists() or (path / "eval").exists():
        return path
    if (path / "data").exists():
        data_dir = path / "data"
        if (data_dir / "fingerprints").exists() or (data_dir / "vuln").exists() or (data_dir / "eval").exists():
            return data_dir
    return None


def discover(explicit_data_dir: str | None = None, explicit_root: str | None = None) -> AIGData | None:
    candidates: list[tuple[Path, str, Path | None]] = []

    if explicit_data_dir:
        p = Path(explicit_data_dir)
        candidates.append((p, "explicit_data_dir", None))
    if explicit_root:
        p = Path(explicit_root)
        candidates.append((p, "explicit_root", p))

    env_data = os.environ.get("AIG_DATA_DIR")
    env_root = os.environ.get("AIG_ROOT")
    if env_data:
        candidates.append((Path(env_data), "env:AIG_DATA_DIR", None))
    if env_root:
        p = Path(env_root)
        candidates.append((p, "env:AIG_ROOT", p))

    for root in DEFAULT_LOCAL_ROOTS:
        candidates.append((root, "default_local_root", root))

    for candidate, source, root_dir in candidates:
        data_dir = _as_data_dir(candidate)
        if data_dir:
            return AIGData(data_dir=data_dir, source=source, root_dir=root_dir)
    return None


def download_to_temp(repo: str = AIG_REPO, keep: bool = False) -> AIGData:
    temp_parent = Path(tempfile.mkdtemp(prefix="aig-agent-redteam-"))
    root = temp_parent / "AI-Infra-Guard"
    cmd = ["git", "clone", "--depth", "1", repo, str(root)]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as e:
        raise RuntimeError("git 不可用，无法下载 AI-Infra-Guard") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"下载 AI-Infra-Guard 失败: {e}") from e

    data_dir = root / "data"
    if not data_dir.exists():
        raise RuntimeError(f"下载成功但未找到 data 目录: {data_dir}")

    data = AIGData(data_dir=data_dir, source="downloaded_temp", root_dir=root)
    if not keep:
        # 调用方仍可在本进程内使用路径；命令行模式需要保留供后续命令使用。
        # 因此 CLI 默认 keep=True，库调用可自行清理。
        pass
    return data


def sync_data(data: AIGData, dest: Path, include: list[str]) -> dict:
    dest = dest.expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    copied = {}
    for name in include:
        src = data.data_dir / name
        if not src.exists():
            copied[name] = {"copied": False, "reason": "source_missing"}
            continue
        dst = dest / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        copied[name] = {"copied": True, "files": len([p for p in dst.rglob("*") if p.is_file()])}
    return {"dest": str(dest), "copied": copied}


def resolve_or_download(args) -> AIGData:
    data = discover(args.aig_data_dir, args.aig_root)
    if data:
        return data
    if args.download:
        return download_to_temp(args.repo, keep=True)
    raise SystemExit("未找到 AIG data。请设置 AIG_DATA_DIR/AIG_ROOT，传 --aig-data-dir/--aig-root，或使用 --download。")


def main() -> None:
    ap = argparse.ArgumentParser(description="解析、下载或同步 AI-Infra-Guard data 目录")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--aig-data-dir", help="AI-Infra-Guard/data 路径")
        p.add_argument("--aig-root", help="AI-Infra-Guard 仓库根目录")
        p.add_argument("--download", action="store_true", help="未找到本地数据时下载 AIG 到临时目录")
        p.add_argument("--repo", default=AIG_REPO, help="AIG git 仓库地址")

    p_status = sub.add_parser("status", help="输出 AIG data 状态 JSON")
    add_common(p_status)

    p_paths = sub.add_parser("paths", help="只输出可供脚本使用的关键路径 JSON")
    add_common(p_paths)

    p_sync = sub.add_parser("sync", help="同步 AIG data 子目录到指定位置")
    add_common(p_sync)
    p_sync.add_argument("--dest", required=True, help="同步目标目录")
    p_sync.add_argument("--include", default="fingerprints,vuln,eval,mcp", help="逗号分隔，如 fingerprints,vuln,eval")

    args = ap.parse_args()
    data = resolve_or_download(args)

    if args.cmd == "status":
        print(json.dumps(data.to_dict(), ensure_ascii=False, indent=2))
    elif args.cmd == "paths":
        print(json.dumps({
            "data_dir": str(data.data_dir),
            "fingerprints_dir": str(data.fingerprints_dir),
            "vuln_dir": str(data.vuln_dir),
            "vuln_en_dir": str(data.vuln_en_dir),
            "eval_dir": str(data.eval_dir),
            "mcp_dir": str(data.mcp_dir),
            "source": data.source,
        }, ensure_ascii=False, indent=2))
    elif args.cmd == "sync":
        include = [x.strip() for x in args.include.split(",") if x.strip()]
        print(json.dumps(sync_data(data, Path(args.dest), include), ensure_ascii=False, indent=2))
    else:
        raise SystemExit(f"未知命令: {args.cmd}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
