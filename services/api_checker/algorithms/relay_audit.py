"""
算法 C：中转站黑盒审计（OpenAI 兼容通用）
==========================================
源自腾讯朱雀实验室 A.I.G（Apache-2.0），7 个探针检测中转站篡改行为。
纯标准库 urllib 实现。
"""

import json
import random
import string
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


CONTENT_MAX_TOKENS = 512

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


def _extract_text(resp):
    try:
        return resp["choices"][0]["message"]["content"] or ""
    except Exception:
        return ""


def _finish_reason(resp):
    try:
        return resp["choices"][0].get("finish_reason")
    except Exception:
        return None


def _is_truncated(resp):
    return _finish_reason(resp) == "length" and not _extract_text(resp).strip()


def _http_json(url, key, body=None, method="POST"):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "aig-api-checker/1.0"}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    start = time.time()
    try:
        with _NO_REDIRECT_OPENER.open(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", "replace")
            lat = int((time.time() - start) * 1000)
            return resp.status, (json.loads(raw) if raw.strip() else {}), lat
    except urllib.error.HTTPError as e:
        lat = int((time.time() - start) * 1000)
        raw = e.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw_error": raw[:1000]}
        return e.code, payload, lat


def _http_stream(url, key, body):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "Accept": "text/event-stream", "User-Agent": "aig-api-checker/1.0"}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    chunks, errors, saw_done = [], [], False
    start = time.time()
    with _NO_REDIRECT_OPENER.open(req, timeout=60) as resp:
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
    return chunks, saw_done, errors, int((time.time() - start) * 1000)


def _chat(base_url, key, model, messages, max_tokens=100, temp=0, stream=False):
    body = {"model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": temp, "stream": stream}
    return _http_json(f"{base_url.rstrip('/')}/chat/completions", key, body)


# ---- 7 个探针 ----
def probe_models(base_url, key, model):
    try:
        status, payload, lat = _http_json(f"{base_url.rstrip('/')}/models", key, method="GET")
        ids = [str(x.get("id", "")) for x in payload.get("data", []) if isinstance(x, dict)] if isinstance(payload.get("data"), list) else []
        return ProbeResult("models", 200 <= status < 300, lat,
            {"status": status, "model_count": len(ids), "target_model_present": model in ids, "sample_models": ids[:20]})
    except Exception as e:
        return ProbeResult("models", False, None, error=str(e))


def probe_liveness(base_url, key, model):
    expected = f"echo-{_rand_str(6)}-{_rand_str(4)}"
    try:
        status, payload, lat = _chat(base_url, key, model,
            [{"role": "user", "content": f"Reply with exactly: {expected}"}], CONTENT_MAX_TOKENS)
        text = _extract_text(payload).strip()
        return ProbeResult("liveness", 200 <= status < 300 and expected in text, lat,
            {"status": status, "expected": expected, "actual": text[:300],
             "finish_reason": _finish_reason(payload), "truncated": _is_truncated(payload),
             "usage": payload.get("usage"), "response_model": payload.get("model")})
    except Exception as e:
        return ProbeResult("liveness", False, None, error=str(e))


def probe_identity(base_url, key, model):
    prompt = random.choice(_IDENTITY_PROMPTS)
    try:
        status, payload, lat = _chat(base_url, key, model, [{"role": "user", "content": prompt}], CONTENT_MAX_TOKENS)
        text = _extract_text(payload).strip()
        hits = [x for x in IDENTITY_KEYWORDS if x in text.lower()]
        return ProbeResult("identity", 200 <= status < 300, lat,
            {"status": status, "identity_text": text[:500], "identity_families": _infer_families(text),
             "response_model": payload.get("model"), "usage": payload.get("usage")})
    except Exception as e:
        return ProbeResult("identity", False, None, error=str(e))


def probe_token_delta(base_url, key, model):
    word = _rand_str(8)
    prompt = f"Return only the word: {word}"
    try:
        status, payload, lat = _chat(base_url, key, model, [{"role": "user", "content": prompt}], 5)
        usage = payload.get("usage") or {}
        actual = usage.get("prompt_tokens")
        expected = max(1, len(prompt) // 4) + 12
        delta = actual - expected if isinstance(actual, int) else None
        return ProbeResult("token_delta", 200 <= status < 300, lat,
            {"status": status, "actual_prompt_tokens": actual, "expected_rough": expected,
             "delta": delta, "usage": usage, "response_model": payload.get("model")})
    except Exception as e:
        return ProbeResult("token_delta", False, None, error=str(e))


def probe_echo_rewrite(base_url, key, model):
    expected = random.choice(_REAL_PIP_COMMANDS)
    prompt = f"Echo this text exactly, no markdown, no explanation:\n{expected}"
    try:
        status, payload, lat = _chat(base_url, key, model, [{"role": "user", "content": prompt}], CONTENT_MAX_TOKENS)
        text = _extract_text(payload).strip()
        suspicious = [x for x in ["curl ", "bash ", "sh ", "unknown", "mirror", " -i http", "wget ", "npm ", "eval("]
                       if x in text.lower()]
        return ProbeResult("echo_rewrite", 200 <= status < 300 and expected in text and not suspicious, lat,
            {"status": status, "expected": expected, "actual": text[:500],
             "exact_match": expected in text, "suspicious_terms": suspicious,
             "response_model": payload.get("model")})
    except Exception as e:
        return ProbeResult("echo_rewrite", False, None, error=str(e))


def probe_stream(base_url, key, model):
    n = random.randint(15, 25)
    body = {"model": model, "messages": [{"role": "user", "content": f"Count from 1 to {n}, separated by spaces."}],
            "max_tokens": CONTENT_MAX_TOKENS, "temperature": 0, "stream": True}
    try:
        chunks, saw_done, errors, lat = _http_stream(f"{base_url.rstrip('/')}/chat/completions", key, body)
        models = sorted({c.get("model") for c in chunks if isinstance(c, dict) and c.get("model")})
        return ProbeResult("stream_integrity", saw_done and not errors and len(chunks) > 0, lat,
            {"chunk_count": len(chunks), "saw_done": saw_done, "json_errors": errors[:5], "stream_models": models})
    except Exception as e:
        return ProbeResult("stream_integrity", False, None, error=str(e))


def probe_context_canary(base_url, key, model):
    s, m, e = f"CANARY_{_rand_str(10)}", f"CANARY_{_rand_str(10)}", f"CANARY_{_rand_str(10)}"
    filler = "The quick brown fox jumps over the lazy dog. " * 120
    content = f"{s}\n{filler}\n{m}\n{filler}\n{e}\n\nRepeat back ONLY the three canary tokens, each on its own line."
    try:
        status, payload, lat = _chat(base_url, key, model, [{"role": "user", "content": content}], CONTENT_MAX_TOKENS)
        text = _extract_text(payload)
        return ProbeResult("context_canary", 200 <= status < 300 and e in text, lat,
            {"status": status, "saw_start": s in text, "saw_mid": m in text, "saw_end": e in text,
             "actual": text.strip()[:300], "response_model": payload.get("model")})
    except Exception as ex:
        return ProbeResult("context_canary", False, None, error=str(ex))


_PROBES = {"models": probe_models, "liveness": probe_liveness, "identity": probe_identity,
           "token_delta": probe_token_delta, "echo_rewrite": probe_echo_rewrite,
           "stream_integrity": probe_stream, "context_canary": probe_context_canary}


# ---- 风险判定 ----
def build_findings(results, requested_model):
    findings = []
    by = {r.name: r for r in results}
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
    if echo and not echo.ok:
        sev, sc, title = ("LOW", 5, "Echo inconclusive (truncated)") if echo.data.get("truncated") else ("HIGH", 35, "Echo/tool command rewrite suspected")
        findings.append(Finding("echo_rewrite", sev, sc, title, str(echo.error or json.dumps(echo.data)), "避免用于编码工作流"))
    stream = by.get("stream_integrity")
    if stream and not stream.ok:
        findings.append(Finding("stream_integrity", "MEDIUM", 20, "Stream integrity anomaly", str(stream.error or json.dumps(stream.data)), "检查 SSE 实现"))
    elif stream and stream.ok:
        sm = stream.data.get("stream_models") or []
        if sm and requested_model not in sm:
            findings.append(Finding("stream_integrity", "MEDIUM", 30, "Stream model field mismatch", json.dumps(stream.data), "流内 model 不一致"))
    canary = by.get("context_canary")
    if canary and canary.ok is False and canary.error is None:
        if canary.data.get("status") and 200 <= int(canary.data.get("status", 0)) < 300:
            if not canary.data.get("truncated"):
                findings.append(Finding("context_canary", "MEDIUM", 20, "Context truncation suspected", json.dumps(canary.data), "尾部 canary 丢失"))
    return findings


def run_relay_audit(base_url, api_key, model, profile="full", cancel_event=None):
    """运行黑盒审计，返回 {score, verdict, findings, probe_results, summary}"""
    probe_names = PROFILES.get(profile, PROFILES["full"])
    results = []
    for name in probe_names:
        if cancel_event is not None and cancel_event.is_set():
            break
        results.append(_PROBES[name](base_url, api_key, model))
    findings = build_findings(results, model)
    score = min(100, sum(f.score for f in findings))
    v = "HIGH" if score >= 70 else ("MEDIUM" if score >= 30 else "LOW")
    v_map = {"LOW": "未发现明显风险", "MEDIUM": "存在可疑", "HIGH": "高风险"}
    return {
        "score": score, "verdict": v, "findings": findings,
        "probe_results": results,
        "summary": f"{v_map[v]} (分数: {score}/100, 发现: {len(findings)} 项)",
    }
