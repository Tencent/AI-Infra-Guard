"""
算法 C：中转站黑盒审计（OpenAI 兼容通用）
==========================================
通过 7 个探针检测中转站篡改行为，使用纯标准库 urllib 实现。
"""

import json
import random
import string
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


CONTENT_MAX_TOKENS = 512
HTTP_TOTAL_TIMEOUT_SECONDS = 60
AUDIT_TOTAL_TIMEOUT_SECONDS = 180

FAMILY_ALIASES = {
    "openai": ["openai", "gpt", "o1", "o3", "o4", "chatgpt"],
    "anthropic": ["anthropic", "claude", "sonnet", "opus", "haiku"],
    "google": ["google", "gemini", "palm", "bard"],
    "qwen": ["qwen", "tongyi"], "deepseek": ["deepseek"],
    "zhipu": ["glm", "zhipu", "chatglm"], "moonshot": ["kimi", "moonshot"],
    "bytedance": ["doubao"], "baidu": ["ernie", "wenxin"],
    "meta": ["llama"], "mistral": ["mistral", "mixtral"],
}
IDENTITY_KEYWORDS = sorted({kw for kws in FAMILY_ALIASES.values() for kw in kws})

_IDENTITY_PROMPTS = [
    "What model are you? Answer in one short sentence.",
    "Which AI model is answering this? Keep it brief.",
    "Identify yourself: what model are you?",
    "In one sentence, what is your model name?",
]
_REAL_PIP_COMMANDS = [
    "pip install requests==2.31.0", "pip install numpy==1.26.4",
    "pip install pandas==2.1.4", "pip install flask==3.0.0",
    "pip install django==5.0.1", "pip install pytest==7.4.3",
    "pip install scipy==1.11.4", "pip install matplotlib==3.8.2",
    "pip install torch==2.1.2", "pip install fastapi==0.109.0",
]

PROBE_NAMES = {
    "models": "模型列表一致性", "liveness": "基础聊天可用性",
    "identity": "模型身份弱信号", "token_delta": "隐藏prompt注入",
    "echo_rewrite": "输出改写检测", "stream_integrity": "流式完整性",
    "context_canary": "上下文截断",
}
PROFILES = {
    "quick": ["models", "liveness", "identity"],
    "standard": ["models", "liveness", "identity", "token_delta", "echo_rewrite", "stream_integrity"],
    "full": ["models", "liveness", "identity", "token_delta", "echo_rewrite", "stream_integrity", "context_canary"],
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)


class _RequestDeadline:
    """在 socket 活跃但响应不结束时也能终止整次 HTTP 请求。"""

    def __init__(self, seconds):
        self._lock = threading.Lock()
        self._response = None
        self.expired = False
        self._timer = threading.Timer(seconds, self._expire)
        self._timer.daemon = True

    def start(self):
        self._timer.start()

    def attach(self, response):
        with self._lock:
            if self.expired:
                response.close()
                raise TimeoutError("HTTP request exceeded total timeout")
            self._response = response

    def _expire(self):
        with self._lock:
            self.expired = True
            response = self._response
        if response is not None:
            response.close()

    def cancel(self):
        self._timer.cancel()
        with self._lock:
            self._response = None

    def raise_if_expired(self):
        if self.expired:
            raise TimeoutError("HTTP request exceeded total timeout")


@dataclass
class Finding:
    probe: str; severity: str; score: int
    title: str; evidence: str; recommendation: str


@dataclass
class ProbeResult:
    name: str; ok: bool; latency_ms: Optional[int]
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


# ---- 工具 ----
def _rand_str(n=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _infer_families(text):
    low = (text or "").lower()
    return [fam for fam, kws in FAMILY_ALIASES.items() if any(kw in low for kw in kws)]


def _model_candidates(model):
    """原始模型优先；带 provider/ 前缀时再尝试去前缀的模型 ID。"""
    candidates = [model]
    if "/" in model:
        unprefixed = model.split("/", 1)[1].strip()
        if unprefixed and unprefixed != model:
            candidates.append(unprefixed)
    return candidates


def _model_id_key(model):
    """用于模型 ID 匹配的规范键：忽略首尾空白和大小写。"""
    return str(model or "").strip().casefold()


def _resolve_listed_model(model, model_ids):
    """从 /models 返回值中选择原始或去前缀后的规范 ID。"""
    canonical = {
        _model_id_key(model_id): model_id
        for model_id in model_ids
        if model_id
    }
    for candidate in _model_candidates(model):
        matched = canonical.get(_model_id_key(candidate))
        if matched:
            return matched
    return None


def _extract_text(resp):
    try:
        return resp["choices"][0]["message"]["content"] or ""
    except Exception:
        pass
    output_text = resp.get("output_text")
    if isinstance(output_text, str):
        return output_text
    texts = []
    for item in resp.get("output", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "output_text" and isinstance(item.get("text"), str):
            texts.append(item["text"])
        for block in item.get("content", []):
            if (
                isinstance(block, dict)
                and block.get("type") in {"output_text", "text"}
                and isinstance(block.get("text"), str)
            ):
                texts.append(block["text"])
    return "".join(texts)


def _finish_reason(resp):
    try:
        return resp["choices"][0].get("finish_reason")
    except Exception:
        pass
    if resp.get("status") == "incomplete":
        details = resp.get("incomplete_details")
        if isinstance(details, dict):
            return details.get("reason") or "incomplete"
        return "incomplete"
    if resp.get("status") == "completed":
        return "stop"
    return None


def _is_truncated(resp):
    reason = _finish_reason(resp)
    return (
        resp.get("status") == "incomplete"
        or (reason in {"length", "max_output_tokens"} and not _extract_text(resp).strip())
    )


def _http_json(url, key, body=None, method="POST", on_request=None):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "aig-api-checker/1.0"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    start = time.time()
    deadline = _RequestDeadline(HTTP_TOTAL_TIMEOUT_SECONDS)
    deadline.start()
    notified = False
    try:
        try:
            resp = _NO_REDIRECT_OPENER.open(
                req,
                timeout=HTTP_TOTAL_TIMEOUT_SECONDS,
            )
        except urllib.error.HTTPError as exc:
            resp = exc
        deadline.attach(resp)
        try:
            raw = resp.read().decode("utf-8", "replace")
        except Exception:
            deadline.raise_if_expired()
            raise
        finally:
            resp.close()
        deadline.raise_if_expired()
        lat = int((time.time() - start) * 1000)
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw_error": raw[:1000]} if raw.strip() else {}
        if on_request:
            on_request(200 <= resp.status < 300)
            notified = True
        return resp.status, payload, lat
    except Exception:
        if on_request and not notified:
            on_request(False)
        raise
    finally:
        deadline.cancel()


def _http_stream(url, key, body, on_request=None):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "Accept": "text/event-stream", "User-Agent": "aig-api-checker/1.0"}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    chunks, errors, saw_done = [], [], False
    start = time.time()
    deadline = _RequestDeadline(HTTP_TOTAL_TIMEOUT_SECONDS)
    deadline.start()
    notified = False
    try:
        resp = _NO_REDIRECT_OPENER.open(
            req,
            timeout=HTTP_TOTAL_TIMEOUT_SECONDS,
        )
        deadline.attach(resp)
        try:
            for line in resp:
                line = line.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    saw_done = True; break
                try:
                    chunks.append(json.loads(payload))
                except Exception:
                    errors.append(payload[:300])
        except Exception:
            deadline.raise_if_expired()
            raise
        finally:
            resp.close()
        deadline.raise_if_expired()
        if on_request:
            on_request(True)
            notified = True
    except Exception:
        if on_request and not notified:
            on_request(False)
        raise
    finally:
        deadline.cancel()
    return chunks, saw_done, errors, int((time.time() - start) * 1000)


def _chat(
    base_url,
    key,
    model,
    messages,
    max_tokens=100,
    temp=None,
    stream=False,
    api_type="openai",
    on_request=None,
):
    candidates = _model_candidates(model)
    total_latency = 0
    for index, candidate in enumerate(candidates):
        if api_type == "openai-responses":
            body = {
                "model": candidate,
                "input": messages,
                "max_output_tokens": max_tokens,
                "stream": stream,
            }
            endpoint = "responses"
        else:
            body = {
                "model": candidate,
                "messages": messages,
                "max_tokens": max_tokens,
                "stream": stream,
            }
            endpoint = "chat/completions"
        if temp is not None:
            body["temperature"] = temp
        status, payload, latency = _http_json(
            f"{base_url.rstrip('/')}/{endpoint}",
            key,
            body,
            on_request=on_request,
        )
        total_latency += latency
        has_fallback = index + 1 < len(candidates)
        if not has_fallback or status not in {400, 404, 422}:
            return status, payload, total_latency, candidate
    return status, payload, total_latency, candidates[-1]


# ---- 7 个探针 ----
def probe_models(base_url, key, model, api_type="openai", on_request=None):
    try:
        status, payload, lat = _http_json(
            f"{base_url.rstrip('/')}/models",
            key,
            method="GET",
            on_request=on_request,
        )
        ids = [str(x.get("id", "")) for x in payload.get("data", []) if isinstance(x, dict)] if isinstance(payload.get("data"), list) else []
        resolved_model = _resolve_listed_model(model, ids)
        return ProbeResult("models", 200 <= status < 300, lat,
            {"status": status, "model_count": len(ids),
             "target_model_present": resolved_model is not None,
             "resolved_model": resolved_model, "sample_models": ids[:20]})
    except Exception as e:
        return ProbeResult("models", False, None, error=str(e))


def probe_liveness(base_url, key, model, api_type="openai", on_request=None):
    expected = f"echo-{_rand_str(6)}-{_rand_str(4)}"
    try:
        status, payload, lat, resolved_model = _chat(base_url, key, model,
            [{"role": "user", "content": f"Reply with exactly: {expected}"}],
            CONTENT_MAX_TOKENS, api_type=api_type, on_request=on_request)
        text = _extract_text(payload).strip()
        return ProbeResult("liveness", 200 <= status < 300 and expected in text, lat,
            {"status": status, "expected": expected, "actual": text[:300],
             "finish_reason": _finish_reason(payload), "truncated": _is_truncated(payload),
             "usage": payload.get("usage"), "response_model": payload.get("model"),
             "resolved_model": resolved_model})
    except Exception as e:
        return ProbeResult("liveness", False, None, error=str(e))


def probe_identity(base_url, key, model, api_type="openai", on_request=None):
    prompt = random.choice(_IDENTITY_PROMPTS)
    try:
        status, payload, lat, resolved_model = _chat(
            base_url, key, model, [{"role": "user", "content": prompt}],
            CONTENT_MAX_TOKENS, api_type=api_type, on_request=on_request)
        text = _extract_text(payload).strip()
        hits = [x for x in IDENTITY_KEYWORDS if x in text.lower()]
        return ProbeResult("identity", 200 <= status < 300, lat,
            {"status": status, "identity_text": text[:500], "identity_families": _infer_families(text),
             "requested_families": _infer_families(model),
             "response_model": payload.get("model"), "usage": payload.get("usage"),
             "resolved_model": resolved_model})
    except Exception as e:
        return ProbeResult("identity", False, None, error=str(e))


def probe_token_delta(base_url, key, model, api_type="openai", on_request=None):
    word = _rand_str(8)
    prompt = f"Return only the word: {word}"
    try:
        status, payload, lat, resolved_model = _chat(
            base_url, key, model, [{"role": "user", "content": prompt}],
            5, api_type=api_type, on_request=on_request)
        usage = payload.get("usage") or {}
        actual = usage.get("prompt_tokens", usage.get("input_tokens"))
        expected = max(1, len(prompt) // 4) + 12
        delta = actual - expected if isinstance(actual, int) else None
        return ProbeResult("token_delta", 200 <= status < 300, lat,
            {"status": status, "actual_prompt_tokens": actual, "expected_rough": expected,
             "delta": delta, "usage": usage, "response_model": payload.get("model"),
             "resolved_model": resolved_model})
    except Exception as e:
        return ProbeResult("token_delta", False, None, error=str(e))


def probe_echo_rewrite(base_url, key, model, api_type="openai", on_request=None):
    expected = random.choice(_REAL_PIP_COMMANDS)
    prompt = f"Echo this text exactly, no markdown, no explanation:\n{expected}"
    try:
        status, payload, lat, resolved_model = _chat(
            base_url, key, model, [{"role": "user", "content": prompt}],
            CONTENT_MAX_TOKENS, api_type=api_type, on_request=on_request)
        text = _extract_text(payload).strip()
        suspicious = [x for x in ["curl ", "bash ", "sh ", "unknown", "mirror", " -i http", "wget ", "npm ", "eval("]
                       if x in text.lower()]
        return ProbeResult("echo_rewrite", 200 <= status < 300 and expected in text and not suspicious, lat,
            {"status": status, "expected": expected, "actual": text[:500],
             "exact_match": expected in text, "suspicious_terms": suspicious,
             "finish_reason": _finish_reason(payload),
             "truncated": _is_truncated(payload),
             "usage": payload.get("usage"), "response_model": payload.get("model"),
             "resolved_model": resolved_model})
    except Exception as e:
        return ProbeResult("echo_rewrite", False, None, error=str(e))


def probe_stream(base_url, key, model, api_type="openai", on_request=None):
    n = random.randint(15, 25)
    messages = [{
        "role": "user",
        "content": f"Count from 1 to {n}, separated by spaces.",
    }]
    if api_type == "openai-responses":
        body = {
            "model": model,
            "input": messages,
            "max_output_tokens": CONTENT_MAX_TOKENS,
            "stream": True,
        }
        endpoint = "responses"
    else:
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": CONTENT_MAX_TOKENS,
            "stream": True,
        }
        endpoint = "chat/completions"
    try:
        chunks, saw_done, errors, lat = _http_stream(
            f"{base_url.rstrip('/')}/{endpoint}",
            key,
            body,
            on_request=on_request,
        )
        response_events = [
            chunk for chunk in chunks
            if isinstance(chunk, dict) and isinstance(chunk.get("response"), dict)
        ]
        response_completed = any(
            chunk.get("type") == "response.completed" for chunk in chunks
            if isinstance(chunk, dict)
        )
        completed = saw_done or (
            api_type == "openai-responses" and response_completed
        )
        models = {
            chunk.get("model") for chunk in chunks
            if isinstance(chunk, dict) and chunk.get("model")
        }
        models.update(
            chunk["response"].get("model") for chunk in response_events
            if chunk["response"].get("model")
        )
        usage = next((
            chunk["response"].get("usage") for chunk in reversed(response_events)
            if isinstance(chunk["response"].get("usage"), dict)
        ), None)
        return ProbeResult(
            "stream_integrity",
            completed and not errors and len(chunks) > 0,
            lat,
            {
                "chunk_count": len(chunks),
                "saw_done": saw_done,
                "response_completed": response_completed,
                "json_errors": errors[:5],
                "stream_models": sorted(models),
                "usage": usage,
            },
        )
    except Exception as e:
        return ProbeResult("stream_integrity", False, None, error=str(e))


def probe_context_canary(base_url, key, model, api_type="openai", on_request=None):
    s, m, e = f"CANARY_{_rand_str(10)}", f"CANARY_{_rand_str(10)}", f"CANARY_{_rand_str(10)}"
    filler = "The quick brown fox jumps over the lazy dog. " * 120
    content = f"{s}\n{filler}\n{m}\n{filler}\n{e}\n\nRepeat back ONLY the three canary tokens, each on its own line."
    try:
        status, payload, lat, resolved_model = _chat(
            base_url, key, model, [{"role": "user", "content": content}],
            CONTENT_MAX_TOKENS, api_type=api_type, on_request=on_request)
        text = _extract_text(payload)
        return ProbeResult("context_canary", 200 <= status < 300 and e in text, lat,
            {"status": status, "saw_start": s in text, "saw_mid": m in text, "saw_end": e in text,
             "finish_reason": _finish_reason(payload),
             "truncated": _is_truncated(payload),
             "actual": text.strip()[:300], "usage": payload.get("usage"),
             "response_model": payload.get("model"),
             "resolved_model": resolved_model})
    except Exception as ex:
        return ProbeResult("context_canary", False, None, error=str(ex))


_PROBES = {"models": probe_models, "liveness": probe_liveness, "identity": probe_identity,
           "token_delta": probe_token_delta, "echo_rewrite": probe_echo_rewrite,
           "stream_integrity": probe_stream, "context_canary": probe_context_canary}


# ---- 风险判定 ----
def build_findings(results, requested_model):
    findings = []
    by = {
        r.name: r
        for r in results
        if not bool((r.data or {}).get("not_executed"))
    }
    m = by.get("models")
    if m and not m.ok:
        findings.append(Finding("models", "MEDIUM", 20, "Model list endpoint failed", str(m.error or m.data), "确认支持 GET /v1/models"))
    elif m and m.data.get("target_model_present") is False:
        findings.append(Finding("models", "MEDIUM", 20, "Requested model not found", json.dumps(m.data), "向中转方确认"))
    live = by.get("liveness")
    if live and not live.ok:
        sev, sc, title = ("LOW", 5, "Liveness inconclusive (truncated)") if live.data.get("truncated") else ("HIGH", 50, "Relay liveness failed")
        findings.append(Finding("liveness", sev, sc, title, str(live.error or json.dumps(live.data)), "检查兼容性"))
    ident = by.get("identity")
    if ident and ident.ok:
        text = ident.data.get("identity_text", "")
        rf = _infer_families(requested_model)
        pf = ident.data.get("identity_families") or _infer_families(text)
        if rf and pf and not (set(rf) & set(pf)):
            findings.append(Finding("identity", "LOW", 15, "Model identity family mismatch", json.dumps({"requested": rf, "reported": pf, "text": text}), "弱信号，需佐证"))
    delta = by.get("token_delta")
    if delta and delta.ok:
        d = delta.data.get("delta")
        if isinstance(d, int) and d > 200:
            findings.append(Finding("token_delta", "MEDIUM", 25, "Large prompt token delta", json.dumps(delta.data), "可能注入隐藏指令"))
    echo = by.get("echo_rewrite")
    if (
        echo
        and not echo.ok
        and isinstance(echo.data.get("status"), int)
        and 200 <= echo.data["status"] < 300
    ):
        sev, sc, title = ("LOW", 5, "Echo inconclusive (truncated)") if echo.data.get("truncated") else ("HIGH", 35, "Echo/tool command rewrite suspected")
        findings.append(Finding("echo_rewrite", sev, sc, title, str(echo.error or json.dumps(echo.data)), "避免用于编码工作流"))
    stream = by.get("stream_integrity")
    if stream and not stream.ok:
        findings.append(Finding("stream_integrity", "MEDIUM", 20, "Stream integrity anomaly", str(stream.error or json.dumps(stream.data)), "检查 SSE 实现"))
    elif stream and stream.ok:
        sm = stream.data.get("stream_models") or []
        stream_model_keys = {_model_id_key(model) for model in sm}
        if sm and _model_id_key(requested_model) not in stream_model_keys:
            findings.append(Finding("stream_integrity", "MEDIUM", 30, "Stream model field mismatch", json.dumps(stream.data), "流内 model 不一致"))
    canary = by.get("context_canary")
    if canary and canary.ok is False and canary.error is None:
        if canary.data.get("status") and 200 <= int(canary.data.get("status", 0)) < 300:
            if not canary.data.get("truncated"):
                findings.append(Finding("context_canary", "MEDIUM", 20, "Context truncation suspected", json.dumps(canary.data), "尾部 canary 丢失"))
    return findings


def run_relay_audit(base_url, api_key, model, profile="full", cancel_event=None,
                    on_progress=None, api_type="openai",
                    on_request_progress=None):
    """运行黑盒审计，返回 {score, verdict, findings, probe_results, summary}"""
    probe_names = PROFILES.get(profile, PROFILES["full"])
    results = []
    started = time.monotonic()
    active_model = model
    request_completed = 0
    request_success = 0
    request_error = 0
    request_total = len(probe_names)
    latest_probe_start = max(
        0,
        AUDIT_TOTAL_TIMEOUT_SECONDS - HTTP_TOTAL_TIMEOUT_SECONDS,
    )
    for index, name in enumerate(probe_names):
        probe_request_count = 0

        def request_done(ok):
            nonlocal probe_request_count
            nonlocal request_completed, request_success, request_error
            nonlocal request_total
            probe_request_count += 1
            if probe_request_count > 1:
                request_total += 1
            request_completed += 1
            if ok:
                request_success += 1
            else:
                request_error += 1
            if on_request_progress:
                on_request_progress(
                    request_completed,
                    request_total,
                    request_success,
                    request_error,
                )

        if cancel_event is not None and cancel_event.is_set():
            break
        # 为最后一个上游请求预留完整的单请求超时时间，保证整轮审计
        # 不会因为临界点刚启动一个新探针而突破总时限。
        if time.monotonic() - started >= latest_probe_start:
            for pending_name in probe_names[index:]:
                results.append(ProbeResult(
                    pending_name,
                    False,
                    None,
                    data={"not_executed": True},
                    error="audit exceeded total timeout",
                ))
                if on_progress:
                    on_progress(len(results), len(probe_names))
            break
        result = _PROBES[name](
            base_url,
            api_key,
            active_model,
            api_type,
            request_done,
        )
        results.append(result)
        resolved_model = result.data.get("resolved_model")
        if isinstance(resolved_model, str) and resolved_model:
            active_model = resolved_model
            status = result.data.get("status")
            if (
                name != "models"
                and isinstance(status, int)
                and 200 <= status < 300
            ):
                models_result = next((
                    probe for probe in results
                    if probe.name == "models"
                ), None)
                if models_result is not None and models_result.ok:
                    # /models 可能是裁剪列表；成功生成比列表缺失更能证明
                    # 模型可用，避免继续报告“未找到请求的模型”。
                    models_result.data["target_model_present"] = True
                    models_result.data["resolved_model"] = resolved_model
        if on_progress:
            on_progress(len(results), len(probe_names))
    findings = build_findings(results, active_model)
    score = min(100, sum(f.score for f in findings))
    v = "HIGH" if score >= 70 else ("MEDIUM" if score >= 30 else "LOW")
    v_map = {"LOW": "未发现明显风险", "MEDIUM": "存在可疑", "HIGH": "高风险"}
    return {
        "score": score, "verdict": v, "findings": findings,
        "probe_results": results,
        "resolved_model": active_model,
        "summary": f"{v_map[v]} (分数: {score}/100, 发现: {len(findings)} 项)",
    }
