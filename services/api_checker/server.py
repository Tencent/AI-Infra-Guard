#!/usr/bin/env python3
"""
aig_api_checker — HTTP API 服务器
==================================
对外暴露两个业务接口：

  GET  /api/v1/relay/models             查询可检测模型
  POST /api/v1/relay/check/stream       API 中转检查 SSE 流式接口

algorithm 字段：
  full  → 算法A 随机数指纹 + 算法C 黑盒审计
          模型 ID 含 sonnet/opus/haiku/fable 时自动识别为 Claude：
          协议切到 anthropic，并【自动叠加】算法B 加密级 signature 检测
  quick → 算法C 黑盒审计 7 探针（OpenAI 兼容中转站）
          选 quick 且模型 ID 识别为 Claude 时，【自动叠加】算法B 加密级 signature 检测
          （B 仅限 Anthropic，不单独暴露，识别到 Claude 默认启动）

base URL 统一约定：所有算法接受同一个 base_url，带不带 /v1 均可，
服务端按各算法的端点拼接约定自动归一化（详见 normalize_openai_base /
anthropic_bases）。

长耗时，SSE 模式：接口持续推送 start/progress/result/done 事件。

运行:
    pip install -r requirements.txt
    python server.py                 # 默认 0.0.0.0:8000
    PORT=9000 python server.py       # 指定端口

交互式文档: http://127.0.0.1:8000/docs  (Swagger UI)
详细接口文档: docs/API.md
"""

import os
import asyncio
import json
import ipaddress
import queue
import re
import socket
import threading
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Literal
from urllib.parse import urlparse

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

if __package__:
    from .algorithms.fingerprint import test_model
    from .algorithms.signature import run_all_checks
    from .algorithms.relay_audit import run_relay_audit
    from .algorithms.common import load_baselines, DEFAULT_BASELINES_PATH
else:
    from algorithms.fingerprint import test_model
    from algorithms.signature import run_all_checks
    from algorithms.relay_audit import run_relay_audit
    from algorithms.common import load_baselines, DEFAULT_BASELINES_PATH

VERSION = "1.7.0"
FINGERPRINT_CONCURRENCY = 5
AUDIT_PROFILE = "full"


def _positive_int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, str(default))))
    except ValueError:
        return default


MAX_CONCURRENT_JOBS = _positive_int_env("AIG_API_CHECKER_MAX_JOBS", 2)
DETECTION_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_JOBS)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


ALLOW_HTTP_TARGETS = _bool_env("AIG_API_CHECKER_ALLOW_HTTP")
ALLOW_PRIVATE_TARGETS = _bool_env("AIG_API_CHECKER_ALLOW_PRIVATE_TARGETS")

DEFAULT_LANGUAGE = "zh"
VERDICT_TEXT = {
    "zh": {
        "native": "原生透传", "suspect": "存在可疑", "proxy": "疑似替身",
        "LOW": "未发现明显风险", "MEDIUM": "存在可疑", "HIGH": "高风险",
    },
    "en": {
        "native": "Native passthrough", "suspect": "Suspicious",
        "proxy": "Suspected substitute", "LOW": "No obvious risk detected",
        "MEDIUM": "Suspicious behavior detected", "HIGH": "High risk",
    },
}
FINDING_FAILED_STATUS = "Failed"
FINDING_TITLE_TEXT = {
    "Model list endpoint failed": {
        "zh": "模型列表接口调用失败",
        "en": "Model list endpoint failed",
    },
    "Requested model not found": {
        "zh": "未找到请求的模型",
        "en": "Requested model not found",
    },
    "Liveness inconclusive (truncated)": {
        "zh": "连通性结果不确定（响应被截断）",
        "en": "Liveness inconclusive (truncated)",
    },
    "Relay liveness failed": {
        "zh": "中转服务连通性检查失败",
        "en": "Relay liveness failed",
    },
    "Model identity family mismatch": {
        "zh": "模型身份系列不匹配",
        "en": "Model identity family mismatch",
    },
    "Large prompt token delta": {
        "zh": "提示词 Token 数量偏差过大",
        "en": "Large prompt token delta",
    },
    "Echo inconclusive (truncated)": {
        "zh": "回显结果不确定（响应被截断）",
        "en": "Echo inconclusive (truncated)",
    },
    "Echo/tool command rewrite suspected": {
        "zh": "疑似改写回显或工具命令",
        "en": "Echo/tool command rewrite suspected",
    },
    "Stream integrity anomaly": {
        "zh": "流式响应完整性异常",
        "en": "Stream integrity anomaly",
    },
    "Stream model field mismatch": {
        "zh": "流式响应模型字段不匹配",
        "en": "Stream model field mismatch",
    },
    "Context truncation suspected": {
        "zh": "疑似上下文截断",
        "en": "Context truncation suspected",
    },
}

# 模型 ID 含以下关键词即识别为 Claude（Anthropic），不依赖外部传参
CLAUDE_MODEL_KEYWORDS = ("claude", "sonnet", "opus", "haiku", "fable")


def is_claude_model(model: str) -> bool:
    """根据模型 ID 判断是否 Claude（决定协议与算法B自动启动）"""
    m = (model or "").lower()
    return any(k in m for k in CLAUDE_MODEL_KEYWORDS)


def _validate_target_address(hostname: str, port: int | None) -> None:
    if ALLOW_PRIVATE_TARGETS:
        return
    try:
        candidates = {
            item[4][0]
            for item in socket.getaddrinfo(
                hostname,
                port,
                type=socket.SOCK_STREAM,
            )
        }
    except socket.gaierror as exc:
        raise HTTPException(400, f"base_url 主机无法解析: {hostname}") from exc
    if not candidates:
        raise HTTPException(400, f"base_url 主机无法解析: {hostname}")
    for candidate in candidates:
        address = ipaddress.ip_address(candidate)
        if not address.is_global:
            raise HTTPException(400, "base_url 不允许指向环回、私网、链路本地或保留地址")


# ================================================================
#  base URL 统一归一化
#  所有算法接受同一个 base_url，带不带 /v1 均可；
#  服务端按各算法模块的端点拼接约定拆成实际使用的 base。
# ================================================================
def normalize_openai_base(base_url: str) -> str:
    """OpenAI 协议统一约定（算法A / 算法C）：返回版本 base。

    - 裸域名（https://api.openai.com）→ 自动补 /v1
    - 已带路径（…/v1、…/api/paas/v4 等自定义版本前缀）→ 原样使用
    - 完整端点（…/chat/completions、…/responses）→ 去掉端点后缀
    """
    b = base_url.rstrip("/")
    for suffix in ("/chat/completions", "/responses"):
        if urlparse(b).path.endswith(suffix):
            b = b[:-len(suffix)]
            break
    return b if urlparse(b).path else b + "/v1"


def openai_api_type(base_url: str) -> str:
    """根据用户提交的完整端点选择 Chat Completions 或 Responses 协议。"""
    path = urlparse(base_url.rstrip("/")).path
    return "openai-responses" if path.endswith("/responses") else "openai"


def anthropic_bases(base_url: str) -> tuple[str, str]:
    """Anthropic 协议归一化，返回 (算法A用, 算法B用)。

    两个算法模块的端点拼接约定不同：
    - 算法A 采样客户端：base + /messages      → base 需含 /v1
    - 算法B signature 客户端：base + /v1/messages → base 需不含 /v1
    """
    b = base_url.rstrip("/")
    if b.endswith("/v1"):
        return b, b[:-len("/v1")]
    return b + "/v1", b


# ================================================================
#  JSON 序列化（dataclass / numpy → 原生类型）
# ================================================================
def _jsonable(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        obj = asdict(obj)
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _jsonable(obj.tolist())
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj


def _envelope(data: Any = None, message: str = "success", status: int = 0) -> dict:
    body = {"status": status, "message": message}
    if data is not None:
        body["data"] = data
    return body


def _detectable_models() -> list[dict[str, Any]]:
    """从当前基准库生成 full 模式的参考模型列表。"""
    models = []
    seen = set()
    for baseline in load_baselines():
        model = str(baseline.get("model", "")).strip()
        name = str(baseline.get("name", "")).strip()
        if not model or model.lower() in seen:
            continue
        seen.add(model.lower())
        models.append({
            "id": model,
            "name": name or model,
            "provider": "anthropic" if is_claude_model(model) else "openai_compatible",
        })

    def model_order(item: dict[str, Any]) -> tuple:
        text = f"{item['id']} {item['name']}".lower()
        if "claude" in text:
            family = 0
        elif "gpt" in text:
            family = 1
        else:
            family = 2
        version = [int(part) for part in re.findall(r"\d+", item["name"])]
        version = (version + [0, 0, 0])[:3]
        return (family, *(-part for part in version))

    return sorted(models, key=model_order)


def _sse(event: str, data: Any) -> str:
    payload = json.dumps(_jsonable(data), ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


# ================================================================
#  统一请求模型
# ================================================================
class DetectRequest(BaseModel):
    algorithm: Literal["full", "quick"] = Field(
        ..., description="算法标注：full=完整检查(A+C) / quick=快速检查(C)。"
                         "算法B(加密级signature)不单独可选，模型ID识别为 Claude 时自动启用")
    base_url: str = Field(..., min_length=1, description="待测 API 基础 URL",
                          examples=["https://relay.example.com/v1"])
    api_key: str = Field(..., min_length=1, description="API 密钥（仅内存使用，不写盘不记录）",
                         examples=["sk-..."])
    model: str = Field(..., min_length=1, description="模型名称，仅支持 models 接口返回的列表。"
                                        "含 claude/sonnet/opus/haiku/fable 自动识别为 "
                                        "Claude：协议切 anthropic 并自动叠加算法B",
                       examples=["claude-sonnet-4-5-20250514"])
    language: Literal["zh", "en"] = Field(
        DEFAULT_LANGUAGE,
        description="结果文本语言；zh=中文，en=英文。仅影响 summary 和 findings.title",
    )

    # ---- algorithm=full 专用 ----
    iterations: int = Field(200, ge=50, le=500, description="[full] 采样次数")
    no_think: bool = Field(True, description="[full] 关闭推理模型思考（加速省钱）")

    def check_url(self):
        self.base_url = self.base_url.strip()
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise HTTPException(400, "base_url 必须是有效的 http:// 或 https:// 地址")
        if parsed.username or parsed.password:
            raise HTTPException(400, "base_url 不允许包含用户名或密码")
        if parsed.query or parsed.fragment:
            raise HTTPException(400, "base_url 不允许包含 query 或 fragment")
        if parsed.scheme == "http" and not ALLOW_HTTP_TARGETS:
            raise HTTPException(
                400,
                "base_url 默认要求 https；可信 HTTP 目标需显式设置 AIG_API_CHECKER_ALLOW_HTTP=1",
            )
        try:
            port = parsed.port
        except ValueError as exc:
            raise HTTPException(400, "base_url 端口无效") from exc
        _validate_target_address(parsed.hostname, port)


# ================================================================
#  各算法执行
# ================================================================
def _resolve_baseline_name(model: str) -> str | None:
    """用请求 model 自动匹配基准 name。"""
    model_l = (model or "").lower()
    for baseline in load_baselines():
        name = str(baseline.get("name", ""))
        model_id = str(baseline.get("model", ""))
        if model_l in {name.lower(), model_id.lower()}:
            return name
    return None


class DetectionCancelled(RuntimeError):
    pass


def _raise_if_cancelled(cancel_event) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise DetectionCancelled("检测已取消")


class ErrorResponse(BaseModel):
    detail: str


def _validation_error_detail(errors: list[dict[str, Any]]) -> str:
    messages = []
    for error in errors:
        location = ".".join(str(part) for part in error.get("loc", ()))
        message = str(error.get("msg") or "字段值无效")
        messages.append(f"{location}: {message}" if location else message)
    return "; ".join(messages) or "请求体字段校验失败"


def _completed_rate(completed: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(min(1.0, max(0.0, completed / total)), 2)


def _run_fingerprint(req: DetectRequest, api_type: str, base_url: str,
                     on_progress=None, cancel_event=None) -> dict:
    """算法 A：随机数指纹测试。api_type/base_url 由调度层按模型 ID 推导后传入。
    返回极简：最像的模型 +（可选）造假判定。"""
    def progress(completed, total, _success, _error):
        if on_progress:
            on_progress({
                "completed_rate": _completed_rate(completed, total),
            })

    _raise_if_cancelled(cancel_event)
    result = test_model(
        api_type,
        base_url,
        req.api_key,
        req.model,
        req.iterations,
        FINGERPRINT_CONCURRENCY,
        progress,
        req.no_think,
        _resolve_baseline_name(req.model),
        cancel_event,
    )
    _raise_if_cancelled(cancel_event)
    if "error" in result:
        raise RuntimeError(str(result["error"]))
    bayes = result["bayes"] or {}
    forgery = bayes.get("forgery") or {}
    out = {
        "best_model": bayes.get("best_model_name"),
        "_posterior": bayes.get("best_posterior"),
        "_forgery_status": forgery.get("status"),
    }
    return out


def _run_signature(req: DetectRequest, base_url: str, cancel_event=None) -> dict:
    """算法 B（隐藏）：加密级 signature 检测，仅 Anthropic。
    skip_fingerprint=True：其内部 30 次指纹采样由算法 A 的大采样覆盖，避免重复。
    返回极简：判定 + 评分。"""
    _raise_if_cancelled(cancel_event)
    try:
        result = run_all_checks(
            base_url,
            req.api_key,
            req.model,
            skip_fingerprint=True,
            skip_latency=False,
            cancel_event=cancel_event,
        )
    except Exception:
        _raise_if_cancelled(cancel_event)
        raise
    _raise_if_cancelled(cancel_event)
    return {
        "verdict": result["verdict"],
        "_score": round(result["score"], 1),
    }


def _run_audit(req: DetectRequest, base_url: str, cancel_event=None,
               on_progress=None, api_type="openai") -> dict:
    """算法 C：黑盒审计 7 探针。base_url 由调度层归一化后传入。
    返回极简：判定 + 评分 + 风险发现（仅严重度+标题）。"""
    def progress(completed, total):
        if on_progress:
            on_progress({
                "completed_rate": _completed_rate(completed, total),
            })

    _raise_if_cancelled(cancel_event)
    result = run_relay_audit(
        base_url,
        req.api_key,
        req.model,
        AUDIT_PROFILE,
        cancel_event=cancel_event,
        on_progress=progress,
        api_type=api_type,
    )
    _raise_if_cancelled(cancel_event)
    test_info = _audit_test_info(result["probe_results"])
    return {
        "verdict": result["verdict"],
        "_risk_score": result["score"],
        "test_info": test_info,
        "findings": [{"probe": f.probe, "severity": f.severity, "title": f.title}
                     for f in result["findings"]],
        "probe_results": [{
            "name": probe.name,
            "ok": probe.ok,
            "latency_ms": probe.latency_ms,
            "error": str(probe.error)[:200] if probe.error else None,
        } for probe in result["probe_results"]],
    }


def _usage_int(usage: dict, *paths: tuple[str, ...]) -> int | None:
    """读取不同 OpenAI 兼容实现使用的 usage 字段，保留“未提供”和 0 的区别。"""
    for path in paths:
        value: Any = usage
        for key in path:
            if not isinstance(value, dict) or key not in value:
                break
            value = value[key]
        else:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return max(0, int(value))
    return None


def _audit_test_info(probes) -> dict:
    input_total = output_total = cache_total = 0
    input_seen = output_seen = cache_seen = False
    generation_latencies = []

    for probe in probes:
        usage = probe.data.get("usage") if isinstance(probe.data, dict) else None
        if not isinstance(usage, dict):
            continue
        input_tokens = _usage_int(
            usage, ("prompt_tokens",), ("input_tokens",),
        )
        output_tokens = _usage_int(
            usage, ("completion_tokens",), ("output_tokens",),
        )
        cache_read_tokens = _usage_int(
            usage,
            ("prompt_cache_hit_tokens",),
            ("cache_read_input_tokens",),
            ("cached_tokens",),
            ("prompt_tokens_details", "cached_tokens"),
            ("input_tokens_details", "cached_tokens"),
        )
        if input_tokens is not None:
            input_total += input_tokens
            input_seen = True
        if output_tokens is not None:
            output_total += output_tokens
            output_seen = True
        if cache_read_tokens is not None:
            cache_total += cache_read_tokens
            cache_seen = True
        if probe.latency_ms is not None:
            generation_latencies.append(probe.latency_ms)

    total_generation_ms = sum(generation_latencies)
    return {
        "latency_ms": (
            round(total_generation_ms / len(generation_latencies))
            if generation_latencies else None
        ),
        "tokens_per_second": (
            round(output_total / (total_generation_ms / 1000), 2)
            if output_seen and total_generation_ms > 0 else None
        ),
        "input_tokens": input_total if input_seen else None,
        "output_tokens": output_total if output_seen else None,
        "cache_read_tokens": cache_total if cache_seen else None,
    }


def _verdict_text(verdict: str, language: str) -> str:
    return VERDICT_TEXT[language][verdict]


def _finding_title(title: str, language: str) -> str:
    translations = FINDING_TITLE_TEXT.get(title)
    if not translations:
        return title
    return translations.get(language, title)


def _fingerprint_summary(fp: dict, language: str = DEFAULT_LANGUAGE) -> str:
    best_model = fp.get("best_model", "?")
    score = (fp.get("_posterior") or 0) * 100
    if language == "en":
        return f"Most similar to {best_model} ({score:.1f}/100)"
    return f"最像 {best_model} ({score:.1f}/100)"


def _signature_summary(sig: dict, language: str = DEFAULT_LANGUAGE) -> str:
    prefix = "[Signature]" if language == "en" else "[签名]"
    return f"{prefix} {_verdict_text(sig['verdict'], language)}"


def _audit_summary(audit: dict, language: str = DEFAULT_LANGUAGE) -> str:
    safety_score = max(0, 100 - int(audit.get("_risk_score", 0)))
    finding_count = len(audit["findings"])
    verdict = _verdict_text(audit["verdict"], language)
    if language == "en":
        finding_label = "finding" if finding_count == 1 else "findings"
        return (f"{verdict} (safety score {safety_score}/100, "
                f"{finding_count} {finding_label})")
    return (f"{verdict} "
            f"(安全分 {safety_score}/100, 发现 {finding_count} 项风险)")


def _result_score(algorithm: str, parts: dict[str, dict]) -> float:
    if algorithm == "full" and parts.get("fingerprint"):
        return round(float(parts["fingerprint"].get("_posterior") or 0) * 100, 1)
    if algorithm == "quick" and parts.get("audit"):
        return round(max(0.0, 100.0 - float(parts["audit"].get("_risk_score") or 0)), 1)
    if parts.get("signature"):
        return round(float(parts["signature"].get("_score") or 0), 1)
    return 0.0


def _result_detail(
    algorithm: str,
    parts: dict[str, dict],
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    findings = []
    for finding in parts.get("audit", {}).get("findings", []):
        localized = dict(finding)
        localized["severity"] = FINDING_FAILED_STATUS
        localized["title"] = _finding_title(
            str(localized.get("title", "")),
            language,
        )
        findings.append(localized)
    detail = {
        "findings": findings,
        "best_model": "",
        "fingerprint": {},
        "test_info": parts.get("audit", {}).get("test_info", {}),
    }
    if algorithm == "full" and parts.get("fingerprint"):
        fingerprint = parts["fingerprint"]
        detail["best_model"] = fingerprint.get("best_model") or ""
        detail["fingerprint"] = {
            "posterior": fingerprint.get("_posterior"),
            "forgery_status": fingerprint.get("_forgery_status"),
        }
    return detail


def _overall_verdict(algorithm: str, parts: dict[str, dict], errors: dict[str, str]) -> str:
    if errors:
        return "inconclusive"
    audit = parts.get("audit")
    if not audit:
        return "inconclusive"
    if (
        audit.get("verdict") != "LOW"
        or audit.get("findings")
        or any(not probe.get("ok") for probe in audit.get("probe_results", []))
    ):
        return "risk"
    signature = parts.get("signature")
    if signature and signature.get("verdict") != "native":
        return "risk"
    if algorithm == "full" and not parts.get("fingerprint"):
        return "inconclusive"
    if algorithm == "full":
        fingerprint = parts["fingerprint"]
        if float(fingerprint.get("_posterior") or 0) < 0.85:
            return "inconclusive"
        forgery_status = fingerprint.get("_forgery_status")
        if forgery_status in {"suspected_known", "unknown_anomaly"}:
            return "risk"
        if forgery_status != "supported":
            return "inconclusive"
    return "pass"


def _run_detect(req: DetectRequest, on_progress=None, cancel_event=None) -> dict:
    """统一检测调度"""
    claude = is_claude_model(req.model)
    openai_type = openai_api_type(req.base_url)

    # ---- quick：黑盒审计（Claude 时自动叠加算法 B）----
    if req.algorithm == "quick":
        parts: dict[str, Any] = {}
        errors: dict[str, str] = {}
        try:
            parts["audit"] = _run_audit(
                req,
                normalize_openai_base(req.base_url),
                cancel_event,
                on_progress,
                openai_type,
            )
        except DetectionCancelled:
            raise
        except Exception as e:
            errors["audit"] = str(e)[:300]
        if claude:                      # 是 Claude → 自动叠加 B（签名验证）
            _, sig_base = anthropic_bases(req.base_url)
            try:
                parts["signature"] = _run_signature(req, sig_base, cancel_event)
            except DetectionCancelled:
                raise
            except Exception as e:
                errors["signature"] = str(e)[:300]
        if not parts:
            raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errors.items()))
        summaries = []
        if "audit" in parts:
            summaries.append(_audit_summary(parts["audit"], req.language))
        if "signature" in parts:
            summaries.append(_signature_summary(parts["signature"], req.language))
        result = {
            "algorithm": "quick",
            "score": _result_score("quick", parts),
            "overall_verdict": _overall_verdict("quick", parts, errors),
            "summary": " | ".join(summaries),
            "detail": _result_detail("quick", parts, req.language),
        }
        return result

    # ---- full：随机数指纹 + 黑盒审计（Claude 时自动叠加算法 B）----
    if claude:
        api_type = "anthropic"
        fp_base, sig_base = anthropic_bases(req.base_url)
    else:
        api_type = openai_type
        fp_base, sig_base = normalize_openai_base(req.base_url), None

    parts = {}
    errors = {}
    try:
        parts["audit"] = _run_audit(
            req,
            normalize_openai_base(req.base_url),
            cancel_event,
            api_type=openai_type,
        )
    except DetectionCancelled:
        raise
    except Exception as e:
        errors["audit"] = str(e)[:300]
    if claude:                          # 算法 B 隐藏：识别到 Claude 默认启动
        try:
            parts["signature"] = _run_signature(req, sig_base, cancel_event)
        except DetectionCancelled:
            raise
        except Exception as e:
            errors["signature"] = str(e)[:300]
    try:
        parts["fingerprint"] = _run_fingerprint(
            req,
            api_type,
            fp_base,
            on_progress,
            cancel_event,
        )
    except DetectionCancelled:
        raise
    except Exception as e:
        errors["fingerprint"] = str(e)[:300]
    if not parts:
        raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errors.items()))
    summaries = []
    if "signature" in parts:
        summaries.append(_signature_summary(parts["signature"], req.language))
    if "fingerprint" in parts:
        prefix = "[Fingerprint]" if req.language == "en" else "[指纹]"
        summaries.append(
            f"{prefix} {_fingerprint_summary(parts['fingerprint'], req.language)}"
        )
    if "audit" in parts:
        prefix = "[Audit]" if req.language == "en" else "[审计]"
        summaries.append(f"{prefix} {_audit_summary(parts['audit'], req.language)}")
    result = {
        "algorithm": "full",
        "score": _result_score("full", parts),
        "overall_verdict": _overall_verdict("full", parts, errors),
        "summary": " | ".join(summaries),
        "detail": _result_detail("full", parts, req.language),
    }
    return result


async def _stream_detect(req: DetectRequest, request: Request, release_slot=None):
    events: queue.Queue[str | None] = queue.Queue()
    cancel_event = threading.Event()

    def emit(event: str, payload: Any):
        events.put(_sse(event, payload))

    def progress(payload: dict):
        emit("progress", _envelope(payload, "progress"))

    def worker():
        try:
            emit("start", _envelope({"algorithm": req.algorithm}, "started"))
            result = _run_detect(
                req,
                on_progress=progress,
                cancel_event=cancel_event,
            )
            emit("result", _envelope(result))
            emit("done", _envelope(message="done"))
        except DetectionCancelled:
            pass
        except Exception as e:
            emit("error", _envelope(message=str(e)[:500], status=1))
        finally:
            events.put(None)
            if release_slot:
                release_slot()

    threading.Thread(target=worker, daemon=True).start()
    last_event = time.monotonic()
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                item = await asyncio.to_thread(events.get, True, 1.0)
            except queue.Empty:
                if time.monotonic() - last_event >= 15:
                    yield ": keepalive\n\n"
                    last_event = time.monotonic()
                continue
            if item is None:
                break
            last_event = time.monotonic()
            yield item
    finally:
        cancel_event.set()

# ================================================================
#  FastAPI 应用
# ================================================================
PUBLIC_ROOT_PATH = os.environ.get("AIG_API_CHECKER_ROOT_PATH", "").strip().rstrip("/")
if PUBLIC_ROOT_PATH and not PUBLIC_ROOT_PATH.startswith("/"):
    PUBLIC_ROOT_PATH = "/" + PUBLIC_ROOT_PATH

app = FastAPI(
    title="AIG API Checker",
    version=VERSION,
    description="AI 模型指纹识别 + API 中转检查 HTTP API。详见 docs/API.md。",
    docs_url=None,
    redoc_url=None,
)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": _validation_error_detail(exc.errors())},
    )


CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("AIG_API_CHECKER_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
@app.get("/ui", include_in_schema=False)
def web_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/docs", include_in_schema=False)
def swagger_docs():
    return get_swagger_ui_html(
        openapi_url=f"{PUBLIC_ROOT_PATH}/openapi.json",
        title=f"{app.title} - Swagger UI",
    )


@app.get("/redoc", include_in_schema=False)
def redoc_docs():
    return get_redoc_html(
        openapi_url=f"{PUBLIC_ROOT_PATH}/openapi.json",
        title=f"{app.title} - ReDoc",
    )


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {
        "status": "ok",
        "version": VERSION,
        "max_jobs": MAX_CONCURRENT_JOBS,
        "allow_http_targets": ALLOW_HTTP_TARGETS,
        "allow_private_targets": ALLOW_PRIVATE_TARGETS,
        "public_root_path": PUBLIC_ROOT_PATH,
    }


@app.get("/api/v1/relay/models", tags=["API 中转检查"],
         summary="查询当前指纹参考模型")
def api_relay_models():
    models = _detectable_models()
    return _envelope({
        "models": models,
        "total": len(models),
        "algorithms": {
            "full": "仅支持 models 列表中的模型，可进行指纹识别和黑盒审计",
            "quick": "仅支持 models 列表中的模型，进行快速检测",
        },
    })


@app.post(
    "/api/v1/relay/check/stream",
    tags=["API 中转检查"],
    summary="API 中转检查 SSE 流式接口。algorithm=full 完整检查 / quick 快速检查",
    responses={
        422: {
            "model": ErrorResponse,
            "description": "请求体字段校验失败",
        },
    },
)
async def api_relay_check_stream(req: DetectRequest, request: Request):
    await asyncio.to_thread(req.check_url)
    if req.algorithm == "full" and not load_baselines():
        raise HTTPException(409, f"基准库为空，请先用 CLI 标定: python main.py calibrate "
                                 f"（基准文件: {DEFAULT_BASELINES_PATH}）")
    if not DETECTION_SLOTS.acquire(blocking=False):
        raise HTTPException(429, "检测任务已满，请稍后重试")
    return StreamingResponse(
        _stream_detect(req, request, release_slot=DETECTION_SLOTS.release),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", "8000")))
