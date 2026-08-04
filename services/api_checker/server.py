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
import hashlib
import json
import ipaddress
import logging
import queue
import re
import socket
import sys
import threading
import time
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
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
    from .algorithms.signature import (
        SIGNATURE_QUICK_REQUEST_COUNT,
        run_all_checks,
    )
    from .algorithms.relay_audit import run_relay_audit
    from .algorithms.common import (
        load_baselines,
        resolve_baseline_name,
        DEFAULT_BASELINES_PATH,
    )
else:
    from algorithms.fingerprint import test_model
    from algorithms.signature import (
        SIGNATURE_QUICK_REQUEST_COUNT,
        run_all_checks,
    )
    from algorithms.relay_audit import run_relay_audit
    from algorithms.common import (
        load_baselines,
        resolve_baseline_name,
        DEFAULT_BASELINES_PATH,
    )

VERSION = "1.7.0"
FINGERPRINT_CONCURRENCY = 5
AUDIT_PROFILE = "full"
QUICK_AUDIT_REQUEST_COUNT = 7


def _log_level() -> tuple[str, int]:
    name = os.environ.get("AIG_API_CHECKER_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, name, None)
    if not isinstance(level, int):
        return "INFO", logging.INFO
    return name, level


LOG_LEVEL_NAME, LOG_LEVEL = _log_level()
LOGGER = logging.getLogger("aig.api_checker")
LOGGER.setLevel(LOG_LEVEL)
LOGGER.propagate = False
if not LOGGER.handlers:
    _log_handler = logging.StreamHandler(sys.stdout)
    _log_handler.setFormatter(logging.Formatter("%(message)s"))
    LOGGER.addHandler(_log_handler)


def _log_event(level: int, event: str, **fields: Any) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "level": logging.getLevelName(level),
        "service": "aig-api-checker",
        "event": event,
    }
    payload.update({key: value for key, value in fields.items() if value is not None})
    LOGGER.log(
        level,
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str),
    )


def _api_key_log_fields(api_key: str) -> dict[str, str]:
    return {
        "api_key_suffix": api_key[-3:],
        "api_key_sha256": hashlib.sha256(api_key.encode("utf-8")).hexdigest(),
    }


def _request_id(value: str | None) -> str:
    if value and re.fullmatch(r"[A-Za-z0-9._-]{1,64}", value):
        return value
    return uuid.uuid4().hex


def _redact_log_text(value: Any, api_key: str) -> str:
    text = str(value)
    return text.replace(api_key, "[REDACTED]") if api_key else text


def _positive_int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, str(default))))
    except ValueError:
        return default


MAX_CONCURRENT_JOBS = _positive_int_env("AIG_API_CHECKER_MAX_JOBS", 20)
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
FINDING_PASSED_STATUS = "Passed"
PROBE_CHECK_TITLE = {
    "models": {
        "zh": "模型列表检查",
        "en": "Model list check",
    },
    "liveness": {
        "zh": "中转服务连通性检查",
        "en": "Relay liveness check",
    },
    "identity": {
        "zh": "模型身份检查",
        "en": "Model identity check",
    },
    "token_delta": {
        "zh": "提示词 Token 差异检查",
        "en": "Prompt token delta check",
    },
    "echo_rewrite": {
        "zh": "回显与工具命令检查",
        "en": "Echo and tool command check",
    },
    "stream_integrity": {
        "zh": "流式响应完整性检查",
        "en": "Stream integrity check",
    },
    "context_canary": {
        "zh": "上下文完整性检查",
        "en": "Context integrity check",
    },
}
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
SPECIALIZED_RISK_CHECKS = [
    {
        "probe": "models",
        "failed_title": "Model list endpoint failed",
        "title": {
            "zh": "模型列表接口调用检查",
            "en": "Model list endpoint check",
        },
    },
    {
        "probe": "models",
        "failed_title": "Requested model not found",
        "title": {
            "zh": "请求模型存在性检查",
            "en": "Requested model presence check",
        },
    },
    {
        "probe": "liveness",
        "failed_title": "Liveness inconclusive (truncated)",
        "title": {
            "zh": "连通性响应截断检查",
            "en": "Liveness truncation check",
        },
    },
    {
        "probe": "liveness",
        "failed_title": "Relay liveness failed",
        "title": {
            "zh": "中转服务连通性专项检查",
            "en": "Relay liveness risk check",
        },
    },
    {
        "probe": "identity",
        "failed_title": "Model identity family mismatch",
        "title": {
            "zh": "模型身份系列匹配检查",
            "en": "Model identity family match check",
        },
    },
    {
        "probe": "token_delta",
        "failed_title": "Large prompt token delta",
        "title": {
            "zh": "提示词 Token 数量偏差检查",
            "en": "Prompt token delta risk check",
        },
    },
    {
        "probe": "echo_rewrite",
        "failed_title": "Echo inconclusive (truncated)",
        "title": {
            "zh": "回显响应截断检查",
            "en": "Echo truncation check",
        },
    },
    {
        "probe": "echo_rewrite",
        "failed_title": "Echo/tool command rewrite suspected",
        "title": {
            "zh": "回显与工具命令改写检查",
            "en": "Echo and tool command rewrite check",
        },
    },
    {
        "probe": "stream_integrity",
        "failed_title": "Stream integrity anomaly",
        "title": {
            "zh": "流式响应异常检查",
            "en": "Stream anomaly check",
        },
    },
    {
        "probe": "stream_integrity",
        "failed_title": "Stream model field mismatch",
        "title": {
            "zh": "流式响应模型字段匹配检查",
            "en": "Stream model field match check",
        },
    },
    {
        "probe": "context_canary",
        "failed_title": "Context truncation suspected",
        "title": {
            "zh": "上下文截断检查",
            "en": "Context truncation check",
        },
    },
]

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
    api_key: str = Field(..., min_length=1,
                         description="API 密钥（原文仅内存使用；日志仅记录后 3 位和 SHA-256）",
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
    """把请求模型 ID 映射到 full 指纹数据集的规范 name。"""
    return resolve_baseline_name(model, load_baselines())


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


def _quick_progress(completed: int, total: int, success: int,
                    error: int) -> dict:
    return {
        "completed": completed,
        "total": total,
        "success": success,
        "error": error,
    }


def _run_fingerprint(req: DetectRequest, api_type: str, base_url: str,
                     on_progress=None, cancel_event=None) -> dict:
    """算法 A：随机数指纹测试。api_type/base_url 由调度层按模型 ID 推导后传入。
    返回极简：最像的模型 +（可选）造假判定。"""
    def progress(completed, total, success, error):
        if on_progress:
            on_progress({
                "completed": completed,
                "total": total,
                "success": success,
                "error": error,
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


def _run_signature(req: DetectRequest, base_url: str, cancel_event=None,
                   on_progress=None) -> dict:
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
            on_progress=on_progress,
        )
    except Exception:
        _raise_if_cancelled(cancel_event)
        raise
    _raise_if_cancelled(cancel_event)
    failed_checks = []
    for check in result.get("checks", []):
        if getattr(check, "passed", False):
            continue
        failed_checks.append({
            "name": str(getattr(check, "name", "Signature")),
            "detail": str(getattr(check, "detail", ""))[:200],
            "critical": bool(getattr(check, "critical", False)),
        })
    failed_checks.sort(key=lambda check: not check["critical"])
    return {
        "verdict": result["verdict"],
        "_score": round(result["score"], 1),
        "_failed_checks": failed_checks,
    }


def _run_audit(req: DetectRequest, base_url: str, cancel_event=None,
               on_progress=None, api_type="openai") -> dict:
    """算法 C：黑盒审计 7 探针。base_url 由调度层归一化后传入。
    返回极简：判定 + 评分 + 风险发现（仅严重度+标题）。"""
    def progress(completed, total, success, error):
        if on_progress:
            on_progress(_quick_progress(
                completed,
                total,
                success,
                error,
            ))

    _raise_if_cancelled(cancel_event)
    result = run_relay_audit(
        base_url,
        req.api_key,
        req.model,
        AUDIT_PROFILE,
        cancel_event=cancel_event,
        api_type=api_type,
        on_request_progress=progress,
    )
    _raise_if_cancelled(cancel_event)
    test_info = _audit_test_info(result["probe_results"])
    return {
        "verdict": result["verdict"],
        "_risk_score": result["score"],
        "_resolved_model": result.get("resolved_model") or req.model,
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


def _probe_status_title(probe: str, passed: bool, language: str) -> str:
    return PROBE_CHECK_TITLE.get(probe, {}).get(language, probe)


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


def _result_score(
    algorithm: str,
    parts: dict[str, dict],
    errors: dict[str, str] | None = None,
) -> float:
    scores = []
    if parts.get("audit"):
        scores.append(
            max(
                0.0,
                100.0 - float(parts["audit"].get("_risk_score") or 0),
            )
        )
    if parts.get("signature"):
        scores.append(float(parts["signature"].get("_score") or 0))
    if algorithm == "full" and parts.get("fingerprint"):
        scores.append(
            float(parts["fingerprint"].get("_posterior") or 0) * 100
        )
    if errors:
        scores.append(0.0)
    return round(min(scores), 1) if scores else 0.0


def _signature_finding(
    signature: dict,
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    verdict = str(signature.get("verdict") or "suspect")
    passed = verdict == "native"
    return {
        "probe": "signature",
        "severity": (
            FINDING_PASSED_STATUS
            if passed else FINDING_FAILED_STATUS
        ),
        "title": (
            "Claude signature verification"
            if language == "en" else "Claude 签名验证"
        ),
    }


def _fingerprint_finding(
    fingerprint: dict,
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    posterior = float(fingerprint.get("_posterior") or 0)
    forgery_status = str(fingerprint.get("_forgery_status") or "")
    passed = posterior >= 0.85 and forgery_status == "supported"

    return {
        "probe": "fingerprint",
        "severity": (
            FINDING_PASSED_STATUS
            if passed else FINDING_FAILED_STATUS
        ),
        "title": (
            "Model fingerprint check"
            if language == "en" else "模型指纹检查"
        ),
    }


def _result_detail(
    algorithm: str,
    parts: dict[str, dict],
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    findings = []
    audit = parts.get("audit", {})
    triggered = {}
    for finding in audit.get("findings", []):
        key = (
            str(finding.get("probe") or ""),
            str(finding.get("title") or ""),
        )
        triggered[key] = finding

    executed_probes = set()
    for probe_result in audit.get("probe_results", []):
        probe = str(probe_result.get("name") or "")
        executed_probes.add(probe)
        passed = bool(probe_result.get("ok"))
        findings.append({
            "probe": probe,
            "severity": (
                FINDING_PASSED_STATUS
                if passed else FINDING_FAILED_STATUS
            ),
            "title": _probe_status_title(probe, passed, language),
        })

    for risk_check in SPECIALIZED_RISK_CHECKS:
        probe = risk_check["probe"]
        if probe not in executed_probes:
            continue
        key = (probe, risk_check["failed_title"])
        finding = triggered.pop(key, None)
        if finding:
            findings.append({
                "probe": probe,
                "severity": FINDING_FAILED_STATUS,
                "title": risk_check["title"][language],
            })
        else:
            findings.append({
                "probe": probe,
                "severity": FINDING_PASSED_STATUS,
                "title": risk_check["title"][language],
            })

    for remaining in triggered.values():
        localized = dict(remaining)
        localized["severity"] = FINDING_FAILED_STATUS
        localized["title"] = PROBE_CHECK_TITLE.get(
            str(localized.get("probe") or ""),
            {},
        ).get(
            language,
            str(localized.get("probe") or "Unknown audit check"),
        )
        findings.append(localized)

    signature = parts.get("signature")
    if signature:
        findings.append(_signature_finding(signature, language))

    fingerprint = parts.get("fingerprint")
    if algorithm == "full" and fingerprint:
        findings.append(_fingerprint_finding(fingerprint, language))

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


def _result_summary(
    algorithm: str,
    parts: dict[str, dict],
    errors: dict[str, str],
    language: str = DEFAULT_LANGUAGE,
) -> str:
    overall_verdict = _overall_verdict(algorithm, parts, errors)
    score = _result_score(algorithm, parts, errors)

    if language == "en":
        headline = {
            "pass": "Overall check passed",
            "risk": "Overall check found issues",
            "inconclusive": "Overall check incomplete",
        }[overall_verdict]
        return f"{headline} ({score:.0f}/100)"

    headline = {
        "pass": "综合检查通过",
        "risk": "综合检查发现异常",
        "inconclusive": "综合检查未完成",
    }[overall_verdict]
    return f"{headline}（{score:.0f}/100）"


def _run_detect(
    req: DetectRequest,
    on_progress=None,
    cancel_event=None,
    on_component_error=None,
) -> dict:
    """统一检测调度"""
    claude = is_claude_model(req.model)
    openai_type = openai_api_type(req.base_url)

    # ---- quick：黑盒审计（Claude 时自动叠加算法 B）----
    if req.algorithm == "quick":
        parts: dict[str, Any] = {}
        errors: dict[str, str] = {}
        effective_req = req
        audit_progress = None
        signature_progress = None
        audit_request_state = {
            "completed": 0,
            "total": QUICK_AUDIT_REQUEST_COUNT,
            "success": 0,
            "error": 0,
        }
        if on_progress:
            def audit_progress(payload: dict):
                audit_request_state.update(payload)
                total = payload["total"]
                if claude:
                    total += SIGNATURE_QUICK_REQUEST_COUNT
                on_progress(_quick_progress(
                    payload["completed"],
                    total,
                    payload["success"],
                    payload["error"],
                ))

            if claude:
                def signature_progress(completed: int, total: int,
                                       success: int, error: int):
                    on_progress(_quick_progress(
                        audit_request_state["completed"] + completed,
                        audit_request_state["total"] + total,
                        audit_request_state["success"] + success,
                        audit_request_state["error"] + error,
                    ))

        try:
            parts["audit"] = _run_audit(
                req,
                normalize_openai_base(req.base_url),
                cancel_event,
                audit_progress,
                openai_type,
            )
            resolved_model = parts["audit"].get("_resolved_model")
            if resolved_model and resolved_model != req.model:
                effective_req = req.model_copy(
                    update={"model": resolved_model},
                )
        except DetectionCancelled:
            raise
        except Exception as e:
            errors["audit"] = str(e)[:300]
            if on_component_error:
                on_component_error("audit", e)
        if claude:                      # 是 Claude → 自动叠加 B（签名验证）
            _, sig_base = anthropic_bases(req.base_url)
            try:
                parts["signature"] = _run_signature(
                    effective_req,
                    sig_base,
                    cancel_event,
                    signature_progress,
                )
            except DetectionCancelled:
                raise
            except Exception as e:
                errors["signature"] = str(e)[:300]
                if on_component_error:
                    on_component_error("signature", e)
        if not parts:
            raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errors.items()))
        score = _result_score("quick", parts, errors)
        overall_verdict = _overall_verdict("quick", parts, errors)
        result = {
            "algorithm": "quick",
            "score": score,
            "overall_verdict": overall_verdict,
            "summary": _result_summary(
                "quick",
                parts,
                errors,
                req.language,
            ),
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
    effective_req = req
    try:
        parts["audit"] = _run_audit(
            req,
            normalize_openai_base(req.base_url),
            cancel_event,
            api_type=openai_type,
        )
        resolved_model = parts["audit"].get("_resolved_model")
        if resolved_model and resolved_model != req.model:
            effective_req = req.model_copy(
                update={"model": resolved_model},
            )
    except DetectionCancelled:
        raise
    except Exception as e:
        errors["audit"] = str(e)[:300]
        if on_component_error:
            on_component_error("audit", e)
    if claude:                          # 算法 B 隐藏：识别到 Claude 默认启动
        try:
            parts["signature"] = _run_signature(
                effective_req,
                sig_base,
                cancel_event,
            )
        except DetectionCancelled:
            raise
        except Exception as e:
            errors["signature"] = str(e)[:300]
            if on_component_error:
                on_component_error("signature", e)
    try:
        parts["fingerprint"] = _run_fingerprint(
            effective_req,
            api_type,
            fp_base,
            on_progress,
            cancel_event,
        )
    except DetectionCancelled:
        raise
    except Exception as e:
        errors["fingerprint"] = str(e)[:300]
        if on_component_error:
            on_component_error("fingerprint", e)
    if not parts:
        raise RuntimeError("; ".join(f"{k}: {v}" for k, v in errors.items()))
    score = _result_score("full", parts, errors)
    overall_verdict = _overall_verdict("full", parts, errors)
    result = {
        "algorithm": "full",
        "score": score,
        "overall_verdict": overall_verdict,
        "summary": _result_summary(
            "full",
            parts,
            errors,
            req.language,
        ),
        "detail": _result_detail("full", parts, req.language),
    }
    return result


async def _stream_detect(
    req: DetectRequest,
    request: Request,
    release_slot=None,
    log_context: dict[str, Any] | None = None,
):
    events: queue.Queue[str | None] = queue.Queue()
    cancel_event = threading.Event()
    context = dict(log_context or {})

    def emit(event: str, payload: Any):
        events.put(_sse(event, payload))

    def progress(payload: dict):
        emit("progress", _envelope(payload, "progress"))
        _log_event(logging.DEBUG, "detection_progress", **context, **payload)

    def worker():
        started = time.monotonic()
        _log_event(logging.INFO, "detection_started", **context)

        def component_error(component: str, error: Exception):
            _log_event(
                logging.WARNING,
                "detection_component_failed",
                **context,
                component=component,
                error_type=type(error).__name__,
                error=_redact_log_text(error, req.api_key)[:500],
            )

        try:
            emit("start", _envelope({"algorithm": req.algorithm}, "started"))
            result = _run_detect(
                req,
                on_progress=progress,
                cancel_event=cancel_event,
                on_component_error=component_error,
            )
            emit("result", _envelope(result))
            emit("done", _envelope(message="done"))
            _log_event(
                logging.INFO,
                "detection_completed",
                **context,
                duration_ms=round((time.monotonic() - started) * 1000),
                score=result.get("score"),
                overall_verdict=result.get("overall_verdict"),
                findings_count=len(result.get("detail", {}).get("findings", [])),
                best_model=result.get("detail", {}).get("best_model") or None,
            )
        except DetectionCancelled:
            _log_event(
                logging.WARNING,
                "detection_cancelled",
                **context,
                duration_ms=round((time.monotonic() - started) * 1000),
            )
        except Exception as e:
            emit("error", _envelope(message=str(e)[:500], status=1))
            _log_event(
                logging.ERROR,
                "detection_failed",
                **context,
                duration_ms=round((time.monotonic() - started) * 1000),
                error_type=type(e).__name__,
                error=_redact_log_text(e, req.api_key)[:500],
            )
        finally:
            events.put(None)
            if release_slot:
                release_slot()

    threading.Thread(target=worker, daemon=True).start()
    last_event = time.monotonic()
    try:
        while True:
            if await request.is_disconnected():
                _log_event(logging.INFO, "client_disconnected", **context)
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
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    request_id = _request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    detail = _validation_error_detail(exc.errors())
    _log_event(
        logging.WARNING,
        "request_validation_failed",
        request_id=request_id,
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
        error=detail,
    )
    return JSONResponse(
        status_code=422,
        content={"detail": detail},
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    if not request_id:
        request_id = _request_id(request.headers.get("X-Request-ID"))
    headers = dict(exc.headers or {})
    headers["X-Request-ID"] = request_id
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
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
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
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
        "log_level": LOG_LEVEL_NAME,
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
    request_id = _request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    log_context = {
        "request_id": request_id,
        "algorithm": req.algorithm,
        "model": req.model,
        "language": req.language,
        "client_ip": request.client.host if request.client else None,
        **_api_key_log_fields(req.api_key),
    }
    _log_event(logging.INFO, "detection_received", **log_context)
    try:
        await asyncio.to_thread(req.check_url)
    except HTTPException as exc:
        _log_event(
            logging.WARNING,
            "detection_rejected",
            **log_context,
            status_code=exc.status_code,
            reason=_redact_log_text(exc.detail, req.api_key),
        )
        raise
    log_context["base_url"] = req.base_url
    if req.algorithm == "full" and not load_baselines():
        detail = (f"基准库为空，请先用 CLI 标定: python main.py calibrate "
                  f"（基准文件: {DEFAULT_BASELINES_PATH}）")
        _log_event(
            logging.WARNING,
            "detection_rejected",
            **log_context,
            status_code=409,
            reason=detail,
        )
        raise HTTPException(409, detail)
    if not DETECTION_SLOTS.acquire(blocking=False):
        _log_event(
            logging.WARNING,
            "detection_rejected",
            **log_context,
            status_code=429,
            reason="detection capacity exhausted",
        )
        raise HTTPException(429, "检测任务已满，请稍后重试")
    _log_event(logging.INFO, "detection_accepted", **log_context)
    return StreamingResponse(
        _stream_detect(
            req,
            request,
            release_slot=DETECTION_SLOTS.release,
            log_context=log_context,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("HOST", "0.0.0.0"),
                port=int(os.environ.get("PORT", "8000")))
