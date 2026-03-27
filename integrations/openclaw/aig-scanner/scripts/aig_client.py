#!/usr/bin/env python3
"""
AIG Client — CLI wrapper for AI-Infra-Guard taskapi.

Usage:
    python3 aig_client.py scan-infra      --targets URL [URL ...]
    python3 aig_client.py scan-ai-tools   --server-url URL | --github-url URL | --local-path PATH
    python3 aig_client.py scan-agent      --agent-id NAME
    python3 aig_client.py scan-model-safety --target-model MODEL --target-token TOKEN --target-base-url URL \
        --eval-model MODEL --eval-token TOKEN --eval-base-url URL
    python3 aig_client.py check-result    [--session-id ID]
    python3 aig_client.py list-agents

Environment:
    AIG_BASE_URL   (required) AIG server root, e.g. http://127.0.0.1:8088/
    AIG_API_KEY    (optional) API key for taskapi auth
    AIG_USERNAME   (optional) defaults to "openclaw"

Only uses Python stdlib (no pip dependencies).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = os.environ.get("AIG_BASE_URL", "").strip().rstrip("/")
API_KEY = os.environ.get("AIG_API_KEY", "")
USERNAME = os.environ.get("AIG_USERNAME", "openclaw")

POLL_INTERVAL = 3  # seconds
POLL_MAX_ATTEMPTS = 5  # total ~15s

# ── HTTP helpers ──────────────────────────────────────────────────────────────


def _headers(content_type: str = "application/json") -> dict[str, str]:
    h: dict[str, str] = {"username": USERNAME}
    if content_type:
        h["Content-Type"] = content_type
    if API_KEY:
        h["API-KEY"] = API_KEY
    return h


def _request(method: str, path: str, body: Any | None = None) -> Any:
    """Make an HTTP request to AIG and return parsed data."""
    if not BASE_URL:
        _die(
            "AIG_BASE_URL is not configured.\n"
            "Please set the AIG service address first, for example:\n"
            "  http://127.0.0.1:8088/\n"
            "  https://aig.example.com/"
        )

    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None

    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        _die(f"AIG API {method} {path} -> HTTP {e.code}")
    except urllib.error.URLError as e:
        _die(
            f"Cannot connect to AIG server at {BASE_URL}.\n"
            f"Make sure AIG is running (docker compose up -d).\n"
            f"Error: {e.reason}"
        )

    if result.get("status") != 0:
        _die(f"AIG API error: {result.get('message', 'unknown error')}")

    return result.get("data")


def _upload_file(file_path: str) -> dict:
    """Upload a file via multipart/form-data. Returns {fileUrl, filename, size}."""
    if not BASE_URL:
        _die(
            "AIG_BASE_URL is not configured.\n"
            "Please set the AIG service address first, for example:\n"
            "  http://127.0.0.1:8088/\n"
            "  https://aig.example.com/"
        )

    import mimetypes

    resolved = os.path.abspath(file_path)
    if not os.path.isfile(resolved):
        _die(f"File not found: {file_path}")

    filename = os.path.basename(resolved)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    # Build multipart body manually (stdlib only)
    boundary = "----AigClientBoundary9876543210"
    with open(resolved, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n"
        f"\r\n"
    ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

    url = f"{BASE_URL}/api/v1/app/taskapi/upload"
    headers: dict[str, str] = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "username": USERNAME,
    }
    if API_KEY:
        headers["API-KEY"] = API_KEY

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        _die(f"Upload failed -> HTTP {e.code}")
    except urllib.error.URLError as e:
        _die(f"Upload failed: {e.reason}")

    if result.get("status") != 0:
        _die(f"Upload failed: {result.get('message', 'unknown error')}")

    return result["data"]


# ── Output helpers ────────────────────────────────────────────────────────────


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _print_submission(session_id: str, task_type: str) -> None:
    print(f"✅ AIG 任务已提交")
    print(f"Session ID: {session_id}")
    print(f"类型: {task_type}")


def _print_status(data: dict) -> None:
    status = data.get("status", "unknown")
    sid = data.get("session_id", "")
    title = data.get("title", "")
    print(f"Session ID: {sid}")
    print(f"状态: {status}")
    if title:
        print(f"标题: {title}")
    log = data.get("log", "")
    if log:
        print(f"日志: {log[:500]}")


def _normalize_github_url(url: str) -> str:
    """Normalize GitHub file/tree URLs to repository root when possible."""
    raw = url.strip()
    if not raw:
        return raw

    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in ("http", "https") or parsed.netloc != "github.com":
        return raw

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return raw

    owner, repo = parts[0], parts[1]
    normalized = f"{parsed.scheme}://{parsed.netloc}/{owner}/{repo}"
    return normalized


# ── Poll after submission ─────────────────────────────────────────────────────


def _poll_status(session_id: str) -> dict:
    """Poll status up to POLL_MAX_ATTEMPTS times. Returns last status data."""
    for i in range(POLL_MAX_ATTEMPTS):
        status_data = _request("GET", f"/api/v1/app/taskapi/status/{session_id}")
        st = status_data.get("status", "")
        if st in ("done", "completed"):
            return status_data
        if st in ("error", "failed", "terminated"):
            return status_data
        if i < POLL_MAX_ATTEMPTS - 1:
            time.sleep(POLL_INTERVAL)
    return status_data


def _submit_and_poll(task_type: str, content: dict) -> None:
    """Submit task, poll status, fetch result if done."""
    payload = {"type": task_type, "content": content}
    data = _request("POST", "/api/v1/app/taskapi/tasks", payload)
    session_id = data["session_id"]
    _print_submission(session_id, task_type)

    print("\n⏳ 轮询任务状态...")
    status_data = _poll_status(session_id)
    st = status_data.get("status", "")

    if st in ("done", "completed"):
        print("✅ 扫描完成，获取结果...\n")
        result = _request("GET", f"/api/v1/app/taskapi/result/{session_id}")
        _format_result(result, task_type)
    elif st in ("error", "failed"):
        print(f"\n❌ 任务失败")
        _print_status(status_data)
    else:
        print(f"\n⏳ 任务仍在执行中 (状态: {st})")
        print(f"Session ID: {session_id}")
        print(f"说明: AIG 后台继续执行，稍后可用以下命令查询:")
        print(f"  python3 aig_client.py check-result --session-id {session_id}")


# ── Result formatting ─────────────────────────────────────────────────────────


def _format_result(result: Any, task_type: str) -> None:
    """Format and print scan result."""
    if not isinstance(result, dict):
        _print_json(result)
        return

    # taskapi/result returns the resultUpdate event body on main.
    # Unwrap the actual scan payload when present.
    if isinstance(result.get("result"), dict):
        result = result["result"]

    # Score
    score = result.get("score")
    if score is not None:
        print(f"安全评分: {score}")

    # Project overview (mcp_scan)
    readme = result.get("readme")
    if readme:
        print(f"\n📋 项目概览:\n{readme}")

    # Findings
    findings = result.get("results")
    if isinstance(findings, list) and findings:
        print(f"\n🔍 发现 {len(findings)} 个安全问题:")
        for i, item in enumerate(findings, 1):
            if isinstance(item, dict):
                severity = item.get("severity", item.get("risk_level", ""))
                title = item.get("title", item.get("name", item.get("vulnerability", "")))
                desc = item.get("description", item.get("detail", ""))
                print(f"\n  [{i}] {severity} - {title}")
                if desc:
                    print(f"      {desc[:200]}")
            else:
                print(f"\n  [{i}] {item}")

    # Screenshots
    screenshots: list[Any] = []
    raw_screenshots = result.get("screenshots", [])
    if isinstance(raw_screenshots, list):
        screenshots.extend(raw_screenshots)

    # ai_infra_scan returns screenshot on each result item using the singular field.
    if isinstance(findings, list):
        for item in findings:
            if isinstance(item, dict):
                if item.get("screenshot"):
                    screenshots.append(item["screenshot"])
                nested_many = item.get("screenshots")
                if isinstance(nested_many, list):
                    screenshots.extend(nested_many)

    # model_redteam_report commonly exposes an attachment CSV.
    attachment = result.get("attachment")
    if attachment:
        print(f"\n📎 附件: {attachment}")

    jailbreak = result.get("jailbreak")
    total = result.get("total")
    if jailbreak is not None and total is not None:
        print(f"\n🚨 越狱成功: {jailbreak}/{total}")

    if screenshots:
        print(f"\n📸 截图:")
        for i, img in enumerate(screenshots, 1):
            url = img if isinstance(img, str) else img.get("url", img.get("screenshot", ""))
            if url:
                if url.startswith("https://"):
                    print(f"  ![AIG screenshot {i}]({url})")
                else:
                    print(f"  [📸 查看截图 {i}]({url})")

    # If no structured fields matched, dump raw JSON
    if score is None and not readme and not findings and not screenshots and not attachment:
        _print_json(result)


# ── Subcommands ───────────────────────────────────────────────────────────────


def cmd_scan_infra(args: argparse.Namespace) -> None:
    content: dict[str, Any] = {"target": args.targets, "timeout": args.timeout}
    if args.auth_header:
        content["headers"] = dict(h.split(":", 1) for h in args.auth_header)
    if args.model and args.token:
        content["model"] = {
            "model": args.model,
            "token": args.token,
            "base_url": args.base_url or "https://api.openai.com/v1",
        }
    _submit_and_poll("ai_infra_scan", content)


def cmd_scan_ai_tools(args: argparse.Namespace) -> None:
    if not args.model or not args.token:
        _die(
            "AI Tool / Skills Scan requires --model and --token.\n"
            "Example: --model gpt-4o --token sk-xxx --base-url https://api.openai.com/v1"
        )

    content: dict[str, Any] = {
        "model": {
            "model": args.model,
            "token": args.token,
            "base_url": args.base_url or "https://api.openai.com/v1",
        },
        "thread": args.thread,
        "language": args.language,
    }

    if args.server_url:
        content["prompt"] = args.server_url
    elif args.github_url:
        content["prompt"] = _normalize_github_url(args.github_url)
    elif args.local_path:
        print("📤 上传本地文件...")
        upload_data = _upload_file(args.local_path)
        print(f"✅ 上传成功: {upload_data.get('filename')} ({upload_data.get('size', 0)} bytes)")
        content["attachments"] = upload_data["fileUrl"]
        content["prompt"] = args.prompt or "审计此 AI 工具 / Skills 项目"
    else:
        _die("Must provide one of: --server-url, --github-url, or --local-path")

    if args.prompt and not args.local_path:
        content["prompt"] = args.prompt
    if args.custom_headers:
        content["headers"] = dict(h.split(":", 1) for h in args.custom_headers)

    _submit_and_poll("mcp_scan", content)


def cmd_scan_agent(args: argparse.Namespace) -> None:
    content: dict[str, Any] = {
        "agent_id": args.agent_id,
        "language": args.language,
    }
    if args.eval_model and args.eval_token:
        content["eval_model"] = {
            "model": args.eval_model,
            "token": args.eval_token,
            "base_url": args.eval_base_url or "https://api.openai.com/v1",
        }
    if args.prompt:
        content["prompt"] = args.prompt
    _submit_and_poll("agent_scan", content)


def cmd_scan_model_safety(args: argparse.Namespace) -> None:
    content: dict[str, Any] = {
        "model": [
            {
                "model": args.target_model,
                "token": args.target_token,
                "base_url": args.target_base_url,
            }
        ],
        "eval_model": {
            "model": args.eval_model,
            "token": args.eval_token,
            "base_url": args.eval_base_url,
        },
    }
    if args.prompt:
        content["prompt"] = args.prompt
    else:
        content["dataset"] = {
            "dataFile": args.datasets or ["JailBench-Tiny"],
            "numPrompts": args.num_prompts,
            "randomSeed": args.random_seed,
        }
    _submit_and_poll("model_redteam_report", content)


def cmd_check_result(args: argparse.Namespace) -> None:
    sid = args.session_id
    if not sid:
        _die("--session-id is required for check-result")

    print(f"🔍 查询任务状态: {sid}")
    status_data = _request("GET", f"/api/v1/app/taskapi/status/{sid}")
    st = status_data.get("status", "")

    if st in ("done", "completed"):
        print("✅ 任务已完成，获取结果...\n")
        result = _request("GET", f"/api/v1/app/taskapi/result/{sid}")
        task_type = status_data.get("title", "").split(":")[0] if status_data.get("title") else ""
        _format_result(result, task_type)
    elif st in ("error", "failed"):
        print("❌ 任务失败")
        _print_status(status_data)
    elif st in ("todo", "doing", "pending", "running"):
        print(f"⏳ 任务仍在执行中")
        _print_status(status_data)

        if args.wait:
            print("\n等待任务完成...")
            status_data = _poll_status(sid)
            st = status_data.get("status", "")
            if st in ("done", "completed"):
                print("✅ 任务已完成\n")
                result = _request("GET", f"/api/v1/app/taskapi/result/{sid}")
                _format_result(result, "")
            else:
                print(f"⏳ 仍在执行 (状态: {st})，请稍后再查")
    else:
        print(f"未知状态: {st}")
        _print_status(status_data)


def cmd_list_agents(args: argparse.Namespace) -> None:
    agents = _request("GET", "/api/v1/knowledge/agent/names")
    if not agents:
        print(f"当前 username={USERNAME} 下没有可见的 Agent 配置")
        print(f"提示: 如果使用 aig-opensource 默认公共配置，尝试 AIG_USERNAME=public_user")
        return
    print(f"可扫描的 Agent 列表 (username={USERNAME}):\n")
    for name in agents:
        print(f"  - {name}")
    print(f"\n共 {len(agents)} 个 Agent")


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AIG Client - AI-Infra-Guard security scanning CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # scan-infra
    p = sub.add_parser("scan-infra", help="AI Infrastructure Scan (CVEs, misconfigs)")
    p.add_argument("--targets", nargs="+", required=True, help="Target URLs, e.g. http://host:11434")
    p.add_argument("--timeout", type=int, default=30, help="Request timeout (default: 30)")
    p.add_argument("--auth-header", nargs="*", help="Custom headers as key:value")
    p.add_argument("--model", help="Analysis model name")
    p.add_argument("--token", help="Model API token")
    p.add_argument("--base-url", help="Model API base URL")

    # scan-ai-tools
    p = sub.add_parser("scan-ai-tools", help="AI Tool / Skills Scan (MCP, Skills, code audit)")
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--server-url", help="Running AI tool service URL")
    target.add_argument("--github-url", help="GitHub repository URL")
    target.add_argument("--local-path", help="Local .zip/.tar.gz archive path")
    p.add_argument("--model", required=True, help="Analysis model name (required)")
    p.add_argument("--token", required=True, help="Model API token (required)")
    p.add_argument("--base-url", help="Model API base URL")
    p.add_argument("--thread", type=int, default=4, help="Concurrency (default: 4)")
    p.add_argument("--language", default="zh", choices=["zh", "en"], help="Report language")
    p.add_argument("--prompt", help="Custom scan prompt")
    p.add_argument("--custom-headers", nargs="*", help="Custom headers as key:value")

    # scan-agent
    p = sub.add_parser("scan-agent", help="Agent Scan (Dify/Coze/custom agents)")
    p.add_argument("--agent-id", required=True, help="Agent config name in AIG Web UI")
    p.add_argument("--language", default="zh", choices=["zh", "en"], help="Report language")
    p.add_argument("--eval-model", help="Eval model name")
    p.add_argument("--eval-token", help="Eval model token")
    p.add_argument("--eval-base-url", help="Eval model base URL")
    p.add_argument("--prompt", help="Extra scan guidance")

    # scan-model-safety
    p = sub.add_parser("scan-model-safety", help="LLM Jailbreak Evaluation (red-team)")
    p.add_argument("--target-model", required=True, help="Target LLM model name")
    p.add_argument("--target-token", required=True, help="Target model API token")
    p.add_argument("--target-base-url", required=True, help="Target model base URL (required)")
    p.add_argument("--eval-model", required=True, help="Evaluator model name (required)")
    p.add_argument("--eval-token", required=True, help="Evaluator model token (required)")
    p.add_argument("--eval-base-url", required=True, help="Evaluator model base URL (required)")
    p.add_argument(
        "--datasets", nargs="+",
        help="Dataset names (default: JailBench-Tiny). Options: JailBench-Tiny, JailbreakPrompts-Tiny, ChatGPT-Jailbreak-Prompts, JADE-db-v3.0, HarmfulEvalBenchmark",
    )
    p.add_argument("--num-prompts", type=int, default=50, help="Number of test prompts (default: 50)")
    p.add_argument("--random-seed", type=int, default=42, help="Random seed (default: 42)")
    p.add_argument("--prompt", help="Custom jailbreak prompt (mutually exclusive with datasets)")

    # check-result
    p = sub.add_parser("check-result", help="Check task status / fetch result")
    p.add_argument("--session-id", required=True, help="Task session ID")
    p.add_argument("--wait", action="store_true", help="Wait and poll if still running")

    # list-agents
    sub.add_parser("list-agents", help="List visible Agent configs")

    args = parser.parse_args()
    cmd_map = {
        "scan-infra": cmd_scan_infra,
        "scan-ai-tools": cmd_scan_ai_tools,
        "scan-agent": cmd_scan_agent,
        "scan-model-safety": cmd_scan_model_safety,
        "check-result": cmd_check_result,
        "list-agents": cmd_list_agents,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
