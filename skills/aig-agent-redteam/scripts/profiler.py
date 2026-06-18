#!/usr/bin/env python3
"""Phase 1: Target profiler.

Reads user raw input (and optional phase0.json from host self-introspection),
emits target_profile.json with detected target_types and extracted attributes.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

THIS_DIR = Path(__file__).resolve().parent
SKILL_ROOT = THIS_DIR.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(SKILL_ROOT / "modules" / "infra-attack" / "scripts"))

from common.http_probe import http_get, normalize_target, is_reachable, http_get_json  # noqa: E402


# Type classification is prompt-driven (see SKILL.md "目标分类与模块调度").
# This script only handles mechanical tasks: URL extraction, HTTP probing, YAML detection.

def looks_like_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s)) or bool(re.match(r"^[\w.\-]+:\d+$", s)) or s in ("localhost", "127.0.0.1")


def extract_url_from_text(s: str) -> Optional[str]:
    """Extract first URL from a possibly mixed natural-language input.

    Handles cases like:
      "红队 http://192.168.1.10:11434"
      "scan this https://github.com/x/y please"
      "测一下 192.168.1.10:11434"
    """
    # First try full URLs
    m = re.search(r"https?://[^\s一-鿿]+", s)
    if m:
        return m.group(0).rstrip(".,;:")
    # Then bare host:port
    m = re.search(r"(?:^|\s)([\w.\-]+:\d{1,5})(?:\s|$)", s)
    if m:
        return m.group(1)
    return None


def looks_like_github(s: str) -> bool:
    return "github.com" in s or "gitlab.com" in s or "bitbucket.org" in s


def looks_like_local_path(s: str) -> bool:
    p = Path(s).expanduser()
    return p.exists()


def looks_like_yaml(s: str) -> bool:
    return s.endswith((".yaml", ".yml")) and Path(s).expanduser().exists()


def detect_yaml_kind(path: Path) -> str:
    """Detect Dify / Coze / LangChain / generic from YAML schema."""
    try:
        import yaml
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            return "generic"
        keys = set(data.keys())
        if {"app", "kind"} <= keys or "model_config" in keys or "user_input_form" in keys:
            return "dify"
        if "bot_id" in keys or "plugins" in keys:
            return "coze"
        if "agent_type" in keys and "tools" in keys:
            return "langchain"
        if "fields" in keys and "name" in keys:
            return "generic_agent"
        return "generic"
    except Exception:
        return "generic"


def probe_http_service(url: str) -> dict:
    """Probe an HTTP target and try to fingerprint common AI services."""
    url = normalize_target(url)
    if not is_reachable(url, timeout=2.0):
        return {"reachable": False, "url": url}
    result = http_get(url, timeout=8.0)
    if not result.matched():
        return {"reachable": False, "url": url, "error": result.error}

    info = {
        "reachable": True,
        "url": url,
        "final_url": result.final_url,
        "status_code": result.status_code,
        "title": result.title,
        "server_header": result.headers.get("Server", ""),
        "body_preview": result.body[:500],
    }

    # Try fingerprint matching with infra-attack engine
    try:
        from fingerprint_engine import FingerprintEngine  # type: ignore
        engine = FingerprintEngine(SKILL_ROOT / "modules" / "infra-attack" / "data" / "fingerprints")
        match = engine.match(url, primary_response=result)
        if match:
            info["fingerprint_match"] = match.product
            info["version"] = match.version
            info["match_path"] = match.path_hit
    except Exception as e:
        info["fingerprint_error"] = str(e)

    # Detect OpenAI-compatible endpoints (Ollama / vLLM / LM Studio / OpenAI)
    fp = info.get("fingerprint_match", "").lower()
    candidates = [f"{url.rstrip('/')}/v1/models", f"{url.rstrip('/')}/api/tags", f"{url.rstrip('/')}/api/version"]
    for cand in candidates:
        data = http_get_json(cand, timeout=3.0)
        if data:
            info.setdefault("api_probes", {})[cand] = data
            if "data" in data and isinstance(data["data"], list):
                info["openai_compatible"] = True
                info["model_endpoint_inferred"] = f"{url.rstrip('/')}/v1"
                info["models_listed"] = [m.get("id") for m in data["data"] if isinstance(m, dict)]
            if "models" in data and isinstance(data["models"], list):  # ollama /api/tags
                info["model_endpoint_inferred"] = f"{url.rstrip('/')}/v1"
                info["models_listed"] = [m.get("name") for m in data["models"] if isinstance(m, dict)]

    return info


def looks_like_self_target(text: str) -> bool:
    keywords = ["测我自己", "扫我自己", "审我自己", "我自己", "我的agent", "我的 agent",
                "我装的", "我加载", "this agent", "scan myself", "audit myself"]
    return any(k in text.lower() for k in keywords)


def detect_repo_kind(path: Path) -> str:
    """Local code path → mcp_server / skill_package / generic_repo."""
    if (path / "SKILL.md").exists():
        return "skill_package"
    # MCP indicators
    mcp_signals = [path / "mcp.json", path / "mcp-config.json", path / "src" / "server.py", path / "server.ts", path / "stdio_server.py"]
    if any(p.exists() for p in mcp_signals):
        return "mcp_server"
    # Common code repo indicators
    if any((path / f).exists() for f in ["package.json", "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml"]):
        return "code_repository"
    return "generic_path"


def build_profile(raw_input: str, phase0: dict) -> dict:
    profile = {
        "schema": "aig-agent-redteam.target-profile.v1",
        "raw_input": raw_input,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_types": [],
        "extracted": {},
        "cascade_targets": [],
        "hints": [],
    }

    text = raw_input.strip()

    # Self-target detection (host agent itself)
    if looks_like_self_target(text):
        profile["target_types"].append("self")
        # Don't embed full phase0 — just reference run_id; downstream modules
        # can re-read phase0.json if they need details (avoids profile bloat)
        if phase0:
            profile["extracted"]["phase0_ref"] = phase0.get("run_id", "phase0.json")
            profile["extracted"]["host_summary"] = {
                "execution_env": phase0.get("host", {}).get("execution_env"),
                "underlying_model": phase0.get("host", {}).get("underlying_model"),
                "loaded_skills_count": len(phase0.get("host", {}).get("loaded_skills", [])),
                "mcp_servers_count": len(phase0.get("host", {}).get("mcp_servers", [])),
                "workdir": phase0.get("host", {}).get("workdir"),
            }
        return profile

    # YAML file → agent definition
    if looks_like_yaml(text):
        path = Path(text).expanduser().resolve()
        kind = detect_yaml_kind(path)
        profile["target_types"].append("agent_definition")
        profile["extracted"]["yaml_path"] = str(path)
        profile["extracted"]["yaml_kind"] = kind
        return profile

    # GitHub / GitLab URL detected BEFORE general HTTP probe (they're code, not infra)
    if looks_like_github(text):
        # Extract just the URL part if input has natural-language prefix/suffix
        url_match = re.search(r"https?://(?:github|gitlab|bitbucket)\.\w+/[\w./\-]+", text)
        clean_url = url_match.group(0) if url_match else text
        profile["target_types"].append("code_repository")
        profile["extracted"]["repo_url"] = clean_url
        if clean_url != text:
            profile["hints"].append(f"从原始输入中抽取到仓库 URL: {clean_url}")
        return profile

    # URL detection — try full match first, then extract from natural-language wrap
    url_to_probe = None
    if looks_like_url(text):
        url_to_probe = text
    else:
        extracted = extract_url_from_text(text)
        if extracted:
            url_to_probe = extracted
            profile["hints"].append(f"从原始输入中抽取到 URL: {extracted}")

    if url_to_probe:
        url = normalize_target(url_to_probe)
        info = probe_http_service(url)
        if info.get("reachable"):
            fp = (info.get("fingerprint_match") or "").lower()
            if fp:
                profile["target_types"].append(f"http_service:{fp}")
            else:
                profile["target_types"].append("http_service:generic")
            profile["extracted"].update(info)
            # Cascade: if OpenAI-compatible endpoint found
            if info.get("openai_compatible"):
                profile["cascade_targets"].append({
                    "target_types": ["llm_endpoint"],
                    "extracted": {
                        "base_url": info["model_endpoint_inferred"],
                        "models_listed": info.get("models_listed", []),
                        "token": "${AIG_TARGET_TOKEN:-not-required-for-local}",
                        "inferred_from": url,
                    }
                })
        else:
            profile["target_types"].append("unknown")
            profile["extracted"]["unreachable_url"] = url
            profile["hints"].append(f"无法连接 {url}，请确认服务在运行或网络可达")
        return profile

    # GitHub / GitLab URL — already handled above
    pass

    # Local path
    if looks_like_local_path(text):
        path = Path(text).expanduser().resolve()
        kind = detect_repo_kind(path)
        if kind == "skill_package":
            profile["target_types"].append("skill_package")
        elif kind == "mcp_server":
            profile["target_types"].append("mcp_server")
        else:
            profile["target_types"].append("local_path:source")
        profile["extracted"]["path"] = str(path)
        profile["extracted"]["repo_kind"] = kind
        return profile

    # Model config from environment (if user only supplied model name)
    import os
    if os.environ.get("AIG_TARGET_BASE_URL") and os.environ.get("AIG_TARGET_TOKEN"):
        profile["target_types"].append("llm_endpoint")
        profile["extracted"]["base_url"] = os.environ["AIG_TARGET_BASE_URL"]
        profile["extracted"]["model"] = text or os.environ.get("AIG_TARGET_MODEL", "")
        profile["extracted"]["token"] = "***ENV***"
        return profile

    # Fallback: unknown
    profile["target_types"].append("unknown")
    profile["hints"].append(
        "无法从输入推断目标类型。请提供以下任一项："
        "\n  - URL（http://host:port 或 https://host）"
        "\n  - GitHub/GitLab 仓库地址"
        "\n  - 本地代码路径或 .yaml 配置文件路径"
        "\n  - 模型 endpoint：同时提供 model 名称 + 设置环境变量 AIG_TARGET_BASE_URL 与 AIG_TARGET_TOKEN"
        "\n  - 'red team myself' / '测我自己' （红队宿主 Agent 自身）"
    )
    return profile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-input", required=True, help="User's raw target description")
    ap.add_argument("--phase0", help="Path to phase0.json from host self-introspection")
    ap.add_argument("--out", required=True, help="Output target_profile.json path")
    args = ap.parse_args()

    phase0 = {}
    if args.phase0:
        try:
            phase0 = json.loads(Path(args.phase0).read_text())
        except Exception:
            pass

    profile = build_profile(args.raw_input, phase0)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
    print(json.dumps(profile, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
