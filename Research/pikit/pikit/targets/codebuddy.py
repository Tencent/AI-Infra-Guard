"""CodeBuddy (DeepSeek) chat backend.

Uses the CodeBuddy / Tencent Copilot endpoint to call DeepSeek models.
Handles token refresh automatically by reusing the auth flow from the
reference client at ``~/Desktop/api/2.py``.

Install with::

    pip install openai   # for ChatCompletion streaming (optional, urllib fallback exists)
"""

from __future__ import annotations

import gzip
import json
import os
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, List, Optional

from .base import Target
from .types import ChatResponse, Message, ToolCall, ToolResult

ENDPOINT = "https://copilot.tencent.com"
DOMAIN = "tencent.sso.codebuddy.cn"
DEFAULT_MODEL = "deepseek-v4-flash-ioa"

AUTH_DIR = Path("~/Library/Application Support/CodeBuddyExtension/Data/Public/auth").expanduser()
ORIGINAL_CANDIDATES = [
    AUTH_DIR / "tclaude-code/Tencent-Cloud.coding-copilot.info",
    AUTH_DIR / "tcodex/Tencent-Cloud.coding-copilot.info",
]
LOCAL_AUTH = Path(os.environ.get(
    "CODEBUDDY_AUTH_PATH",
    str(Path(__file__).resolve().parent.parent.parent / "codebuddy_auth.info"),
))


def _load_info(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data.get("auth"), dict):
        raise SystemExit(f"invalid auth info file: {path}")
    return data


def _save_info_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _ensure_auth() -> Path:
    if LOCAL_AUTH.exists():
        return LOCAL_AUTH
    for src in ORIGINAL_CANDIDATES:
        if src.exists():
            shutil.copyfile(src, LOCAL_AUTH)
            return LOCAL_AUTH
    raise SystemExit(
        "未找到 CodeBuddy 插件登录凭证，请先在插件里登录。\n"
        f"查找过: {[str(p) for p in ORIGINAL_CANDIDATES]}"
    )


def _headers_for(info: dict, *, include_refresh: bool = False) -> dict:
    auth = info["auth"]
    account = info.get("account") or {}
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-Domain": auth.get("domain") or DOMAIN,
        "X-Product": "SaaS",
        "User-Agent": "CLI/2.100.2 CodeBuddy/2.100.2",
    }
    if auth.get("accessToken"):
        headers["Authorization"] = f"Bearer {auth['accessToken']}"
    if account.get("uid"):
        headers["X-User-Id"] = account["uid"]
    enterprise_id = account.get("enterpriseId")
    if enterprise_id:
        headers["X-Enterprise-Id"] = enterprise_id
        headers["X-Tenant-Id"] = enterprise_id
    if include_refresh:
        headers["X-Refresh-Token"] = auth["refreshToken"]
        headers["X-Auth-Refresh-Source"] = "plugin"
    return headers


def _token_expired(auth: dict) -> bool:
    exp = auth.get("expiresAt")
    if not exp:
        return False
    if exp < 10**12:
        exp *= 1000
    return time.time() * 1000 > exp - 60_000


def _refresh(path: Path) -> dict:
    info = _load_info(path)
    url = ENDPOINT + "/v2/plugin/auth/token/refresh"
    body = json.dumps({}).encode()
    req = urllib.request.Request(url, data=body, headers=_headers_for(info, include_refresh=True), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read()
            if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                payload = gzip.decompress(payload)
            data = (json.loads(payload.decode("utf-8")).get("data")) or {}
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"刷新 token 失败 HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}") from exc
    if not data.get("accessToken"):
        raise SystemExit("刷新 token 响应异常，缺少 accessToken")
    data["lastRefreshTime"] = int(time.time() * 1000)
    info["auth"] = data
    _save_info_atomic(path, info)
    return info


def _ensure_valid_auth() -> dict:
    auth_path = _ensure_auth()
    info = _load_info(auth_path)
    if _token_expired(info["auth"]) or not info["auth"].get("accessToken"):
        info = _refresh(auth_path)
    return info


def _chat_headers(info: dict) -> dict:
    now = int(time.time() * 1000)
    headers = _headers_for(info)
    headers.update({
        "Accept": "application/json",
        "X-Conversation-ID": f"external-info-{now}",
        "X-Conversation-Request-ID": f"external-request-{now}",
        "X-Conversation-Message-ID": f"external-message-{now}",
        "X-Agent-Intent": "craft",
        "X-Agent-Purpose": "conversation",
        "X-IDE-Type": "CLI",
        "X-IDE-Name": "CLI",
        "X-IDE-Version": "2.100.2",
        "x-codebuddy-request": "1",
    })
    return headers


def _solve_eo_bot_challenge(raw_resp: str) -> dict:
    """Parse the TencentEdgeOne EO Bot challenge JS and compute cookies.

    The challenge sets two cookies via document.cookie:
      1. __tst_status=<number>#
      2. EO_Bot_Ssid=<number>

    The JS is obfuscated but the logic is straightforward:
      - t = WTKkN + bOYDu + wyeCN  (three numbers in the `e` object)
      - ssid = the argument to iTyzs(t, NUMBER) in case 3 of function n()
    """
    import re as _re

    # Extract t component numbers (WTKkN, bOYDu, wyeCN values)
    t_nums = _re.findall(r'(?:WTKkN|bOYDu|wyeCN):(\d+)', raw_resp)
    if len(t_nums) >= 3:
        t_val = int(t_nums[0]) + int(t_nums[1]) + int(t_nums[2])
    else:
        t_val = 0

    # Extract SSID number: the argument to iTyzs(t, NUMBER) in case 3
    # Pattern in obfuscated JS: case"3":t=a[_0x649a("0x7")](t,NUMBER)
    ssid_match = _re.search(r'case"3":t=a\[.*?\]\(t,\s*(\d+)\)', raw_resp)
    if ssid_match:
        ssid_val = ssid_match.group(1)
    else:
        # Fallback: find all large numbers not in t_nums
        all_nums = _re.findall(r'(\d{8,})', raw_resp)
        t_set = set(t_nums)
        candidates = [n for n in all_nums if n not in t_set]
        ssid_val = candidates[0] if candidates else "0"

    return {
        "__tst_status": f"{t_val}#",
        "EO_Bot_Ssid": ssid_val,
    }


def _parse_sse_stream(resp) -> str:
    """Parse a streaming SSE response and concatenate content + tool_call deltas.

    Tool calls arrive in fragments across multiple SSE chunks:
    the first chunk carries ``id`` + ``function.name``, subsequent chunks
    carry ``function.arguments`` pieces. We accumulate by ``index``.
    """
    full_text = []
    # Accumulate tool_calls by index: {index: {"id": ..., "name": ..., "arguments": ""}}
    tc_accum: dict[int, dict] = {}

    for line in resp:
        text = line.decode("utf-8", errors="replace").strip()
        if not text.startswith("data:"):
            continue
        data = text[5:].strip()
        if data == "[DONE]":
            break
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        choice = (obj.get("choices") or [{}])[0]
        delta = choice.get("delta") or choice.get("message") or {}
        content = delta.get("content") or ""
        if content:
            full_text.append(content)

        if delta.get("tool_calls"):
            for tc in delta["tool_calls"]:
                idx = tc.get("index", 0)
                if idx not in tc_accum:
                    tc_accum[idx] = {"id": "", "name": "", "arguments": ""}
                fn = tc.get("function") or {}
                if tc.get("id"):
                    tc_accum[idx]["id"] = tc["id"]
                if fn.get("name"):
                    tc_accum[idx]["name"] = fn["name"]
                if fn.get("arguments"):
                    tc_accum[idx]["arguments"] += fn["arguments"]

    # Build final tool_calls list sorted by index.
    tool_calls_raw = [
        {
            "id": v["id"] or f"call_{idx}",
            "type": "function",
            "function": {"name": v["name"], "arguments": v["arguments"]},
        }
        for idx, v in sorted(tc_accum.items())
    ]
    return "".join(full_text), tool_calls_raw


def _parse_non_stream(resp) -> tuple[str, list]:
    """Parse a non-streaming JSON response."""
    payload = resp.read()
    if resp.headers.get("Content-Encoding", "").lower() == "gzip":
        payload = gzip.decompress(payload)
    obj = json.loads(payload.decode("utf-8"))
    choice = (obj.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    text = msg.get("content") or ""
    tool_calls = msg.get("tool_calls") or []
    return text, tool_calls


class CodeBuddyTarget(Target):
    """DeepSeek via CodeBuddy / Tencent Copilot endpoint.

    Supports both :meth:`query` (simple text completion) and :meth:`chat`
    (multi-turn tool-calling) by translating pikit's normalized messages
    into the OpenAI-compatible wire format expected by the endpoint.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.model = model or DEFAULT_MODEL
        self.name = f"codebuddy:{self.model}"
        self._stream = kwargs.get("stream", True)  # CodeBuddy requires streaming
        self._max_retries = kwargs.get("max_retries", 2)
        self._waf_cookie: Optional[str] = None  # cached EO Bot cookie

    def _send(self, body: dict) -> tuple[str, list]:
        """Send a chat completion request, retrying on auth failure and rate limits."""
        import time as _time

        max_rate_retries = 8
        base_backoff = 5.0  # seconds; 5,10,20,40,80,160,320,640 = ~21 min max

        for attempt in range(self._max_retries + 1):
            info = _ensure_valid_auth()
            headers = _chat_headers(info)
            # Attach cached WAF cookie if available
            if self._waf_cookie:
                headers["Cookie"] = self._waf_cookie
            raw_body = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
            req = urllib.request.Request(
                ENDPOINT + "/v2/chat/completions",
                data=raw_body,
                headers=headers,
                method="POST",
            )
            try:
                resp = urllib.request.urlopen(req, timeout=180)
            except urllib.error.HTTPError as exc:
                if exc.code == 401 and attempt < self._max_retries:
                    exc.close()
                    _refresh(_ensure_auth())
                    continue
                if exc.code == 429:
                    exc.close()
                    # Exponential backoff for rate limiting.
                    for rate_attempt in range(max_rate_retries):
                        wait = base_backoff * (2 ** rate_attempt)
                        _time.sleep(wait)
                        info = _ensure_valid_auth()
                        headers = _chat_headers(info)
                        req = urllib.request.Request(
                            ENDPOINT + "/v2/chat/completions",
                            data=raw_body,
                            headers=headers,
                            method="POST",
                        )
                        try:
                            resp = urllib.request.urlopen(req, timeout=180)
                            break
                        except urllib.error.HTTPError as exc2:
                            exc2.close()
                            if exc2.code == 429 and rate_attempt < max_rate_retries - 1:
                                continue
                            if exc2.code == 401:
                                _refresh(_ensure_auth())
                                continue
                            raise SystemExit(
                                f"chat HTTP {exc2.code} {exc2.reason}: "
                                f"{exc2.read().decode('utf-8', errors='replace')}"
                            ) from exc2
                    else:
                        raise RuntimeError("rate limit: max retries exhausted (429)")
                raise SystemExit(
                    f"chat HTTP {exc.code} {exc.reason}: "
                    f"{exc.read().decode('utf-8', errors='replace')}"
                ) from exc

            # --- WAF (TencentEdgeOne EO Bot) challenge detection ---
            # Peek at the response: if Content-Type is text/html, it's the
            # JS challenge page, not an SSE stream. Solve it and retry.
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" in content_type:
                challenge_body = resp.read().decode("utf-8", errors="replace")
                if "EO_Bot_Ssid" in challenge_body:
                    cookies = _solve_eo_bot_challenge(challenge_body)
                    _time.sleep(1.5)  # JS uses setTimeout 0x4b0 (1200ms)
                    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
                    self._waf_cookie = cookie_str  # cache for reuse
                    headers["Cookie"] = cookie_str
                    req2 = urllib.request.Request(
                        ENDPOINT + "/v2/chat/completions",
                        data=raw_body,
                        headers=headers,
                        method="POST",
                    )
                    resp = urllib.request.urlopen(req2, timeout=180)
                    content_type = resp.headers.get("Content-Type", "")
                # If still html after challenge, fall through to normal parsing
                # which will produce empty results

            with resp:
                if body.get("stream") and "text/event-stream" in content_type:
                    return _parse_sse_stream(resp)
                elif not body.get("stream") and "application/json" in content_type:
                    return _parse_non_stream(resp)
                else:
                    # Fallback: try SSE parsing anyway, or non-stream
                    if body.get("stream"):
                        return _parse_sse_stream(resp)
                    else:
                        return _parse_non_stream(resp)
        raise SystemExit("max retries exceeded on auth failure")

    def query(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": self.model,
            "messages": messages,
            "stream": self._stream,
        }
        body.update(kwargs)
        text, _ = self._send(body)
        return text

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[dict]] = None,
        system: Optional[str] = None,
        **kwargs,
    ) -> ChatResponse:
        wire = []
        if system:
            wire.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                wire.append({
                    "role": "assistant",
                    "content": m.content or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.args),
                            },
                        }
                        for tc in m.tool_calls
                    ],
                })
            elif m.role == "tool":
                for tr in m.tool_results:
                    wire.append({
                        "role": "tool",
                        "tool_call_id": tr.id,
                        "content": tr.content,
                    })
            else:
                wire.append({"role": m.role, "content": m.content})

        body = {
            "model": self.model,
            "messages": wire,
            "stream": self._stream,
        }
        if tools:
            body["tools"] = [
                {"type": "function", "function": t} for t in tools
            ]
            body["tool_choice"] = "auto"
        body.update(kwargs)

        text, tool_calls_raw = self._send(body)

        calls = []
        for tc in tool_calls_raw:
            fn = tc.get("function") or tc
            tc_id = tc.get("id", f"call-{len(calls)}")
            tc_name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except (json.JSONDecodeError, TypeError):
                args = {}
            calls.append(ToolCall(id=tc_id, name=tc_name, args=args))

        return ChatResponse(
            text=text,
            tool_calls=calls,
            stop_reason="tool_calls" if calls else "stop",
        )
