"""Utilities to orchestrate DeepSeek sequence tests driven by configuration."""

from __future__ import annotations

import json
import logging
import math
import os
import random
import re
import time
import threading
import concurrent.futures
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, MutableMapping, Optional, Sequence

import requests

from .. import check

__all__ = [
    "SkipVendor",
    "UnifiedClient",
    "normalize_to_digit_series",
    "slugify",
    "now_iso_for_filename",
    "sanitize_for_json",
    "default_run_once",
    "run_tests",
]

_TRANSIENT_HTTP_STATUS = {408, 429, 500, 502, 503, 504}
_DEFAULT_MAX_INFLIGHT_REF_REQUESTS = 6
_DEFAULT_DATA_DIR = os.environ.get(
    "AIG_API_CHECKER_DATA_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "runtime")),
)
_DEFAULT_RESULT_DIR = os.path.join(_DEFAULT_DATA_DIR, "qtest", "result", "json")
_RATE_LIMIT_COOLDOWN_SEC = 60.0
_RATE_LIMIT_LOCK = threading.Lock()
_RATE_LIMIT_UNTIL = 0.0
_QUESTION_MODE_SEQUENTIAL = "sequential"
_QUESTION_MODE_RANDOM_PER_RUN = "random_per_run"


def _normalize_question_mode(raw: Any) -> str:
    mode = str(raw or _QUESTION_MODE_SEQUENTIAL).strip().lower()
    if mode in {"", _QUESTION_MODE_SEQUENTIAL, "ordered"}:
        return _QUESTION_MODE_SEQUENTIAL
    if mode in {
        _QUESTION_MODE_RANDOM_PER_RUN,
        "random",
        "random_each_run",
        "random_per_request",
        "random_each_request",
    }:
        return _QUESTION_MODE_RANDOM_PER_RUN
    raise ValueError(
        "invalid question_mode: "
        f"{raw!r} (expected one of sequential|random_per_run)"
    )


def _wait_for_global_rate_limit(source: str) -> None:
    while True:
        with _RATE_LIMIT_LOCK:
            wait = _RATE_LIMIT_UNTIL - time.monotonic()
        if wait <= 0:
            return
        logging.warning("[%s] 全局 429 暂停中，等待 %.1f 秒", source, wait)
        time.sleep(wait)


def _trigger_global_rate_limit_pause(source: str, status: int = 429) -> None:
    global _RATE_LIMIT_UNTIL
    now = time.monotonic()
    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_UNTIL = max(_RATE_LIMIT_UNTIL, now + _RATE_LIMIT_COOLDOWN_SEC)
        wait = _RATE_LIMIT_UNTIL - now
    logging.warning("[%s] 命中 HTTP %s，触发全局暂停 %.0f 秒", source, status, wait)


class SkipVendor(Exception):
    """Non-fatal error signalling a vendor should be skipped for this run."""

    def __init__(self, vendor: str, status: int | None = None, message: str = "", body: str | None = None):
        self.vendor = vendor
        self.status = status
        self.body = body or ""
        detail = f"{vendor} skipped"
        if status is not None:
            detail += f" (HTTP {status})"
        if message:
            detail += f": {message}"
        if body:
            detail += f" | body={body}"
        super().__init__(detail)


class UnifiedClient:
    """Uniform interface for vendors supporting the `generate` method."""

    def __init__(self, conf: MutableMapping[str, Any], *, timeout: Optional[float] = None):
        self.name = conf["name"]
        self.base_url = conf["base_url"].rstrip("/")
        self.path = conf["path"]
        self.api_key = conf["api_key"]
        self.model = conf["model"]
        self.schema = conf.get("schema", "openai")
        self.extra_headers = dict(conf.get("extra_headers", {}))
        self.provider = conf.get("provider")
        self.extra_payload = dict(conf.get("extra_payload", {}))
        self.timeout = conf.get("timeout", timeout)
        self.max_tokens = conf.get("max_tokens", 400)
        # Repeated-request AFL uses an exact, total outcome map.  Keep the
        # historical stripped response everywhere else, but let that runner
        # preserve whitespace and other nonconforming output verbatim.
        self.strip_response = bool(conf.get("strip_response", True))
        self.max_retries = max(0, int(conf.get("max_retries", 2)))
        self.retry_backoff_sec = max(0.0, float(conf.get("retry_backoff_sec", 1.0)))

    # ------------------------------------------------------------------
    def _url(self) -> str:
        return f"{self.base_url}{self.path}"

    def _headers(self) -> Dict[str, str]:
        if self.schema == "anthropic":
            headers = {"Content-Type": "application/json", "x-api-key": self.api_key}
        else:
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        headers.update(self.extra_headers)
        return headers

    @staticmethod
    def _extract_message_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            if isinstance(content.get("text"), str):
                return content.get("text", "")
            if "content" in content:
                return UnifiedClient._extract_message_text(content.get("content"))
            return ""
        if isinstance(content, list):
            chunks: List[str] = []
            for item in content:
                if isinstance(item, str):
                    chunks.append(item)
                    continue
                if not isinstance(item, dict):
                    continue
                if isinstance(item.get("text"), str):
                    chunks.append(item.get("text", ""))
                    continue
                if "content" in item:
                    text = UnifiedClient._extract_message_text(item.get("content"))
                    if text:
                        chunks.append(text)
            return "".join(chunks)
        return ""

    @classmethod
    def _extract_openai_text(cls, data: Dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        first = choices[0]
        if not isinstance(first, dict):
            return ""

        message = first.get("message")
        if isinstance(message, dict):
            text = cls._extract_message_text(message.get("content"))
            if text:
                return text

        if isinstance(first.get("text"), str):
            return first.get("text", "")
        return ""

    @staticmethod
    def _is_retryable_exception(exc: requests.RequestException) -> bool:
        status = getattr(exc.response, "status_code", None)
        if status in _TRANSIENT_HTTP_STATUS:
            return True
        return isinstance(exc, (requests.Timeout, requests.ConnectionError))

    def _retry_wait(self, attempt: int) -> float:
        # attempt starts at 1
        return self.retry_backoff_sec * (2 ** max(0, attempt - 1))

    # ------------------------------------------------------------------
    def generate(self, prompt: str, *, temperature: float = 0.6) -> str:
        url = self._url()
        headers = self._headers()
        timeout = self.timeout
        max_attempts = self.max_retries + 1

        if self.schema == "openai":
            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.max_tokens,
                "temperature": temperature,
                "stream": False,
            }
            if self.provider:
                payload["provider"] = self.provider
            if self.extra_payload:
                payload.update(self.extra_payload)

            for attempt in range(1, max_attempts + 1):
                _wait_for_global_rate_limit(self.name)
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
                except requests.RequestException as exc:  # pragma: no cover - network failure path
                    status = getattr(exc.response, "status_code", None)
                    if status == 429:
                        _trigger_global_rate_limit_pause(self.name, status=429)
                    if attempt < max_attempts and self._is_retryable_exception(exc):
                        wait = self._retry_wait(attempt)
                        logging.warning(
                            "[%s] 请求异常，第 %d/%d 次重试前等待 %.1fs: %s",
                            self.name,
                            attempt,
                            max_attempts,
                            wait,
                            exc,
                        )
                        time.sleep(wait)
                        continue
                    raise SkipVendor(self.name, status, str(exc)) from None

                status = response.status_code
                if status in _TRANSIENT_HTTP_STATUS:
                    if status == 429:
                        _trigger_global_rate_limit_pause(self.name, status=429)
                    if attempt < max_attempts:
                        wait = self._retry_wait(attempt)
                        logging.warning(
                            "[%s] 命中 HTTP %s，第 %d/%d 次重试前等待 %.1fs",
                            self.name,
                            status,
                            attempt,
                            max_attempts,
                            wait,
                        )
                        time.sleep(wait)
                        continue
                    raise SkipVendor(self.name, status, body=response.text[:200])

                try:
                    response.raise_for_status()
                except requests.RequestException as exc:
                    status = getattr(exc.response, "status_code", None)
                    raise SkipVendor(self.name, status, str(exc), body=response.text[:200]) from None

                try:
                    data = response.json()
                except Exception as exc:
                    raise SkipVendor(self.name, status, f"invalid JSON: {exc}", body=response.text[:200]) from None

                text = self._extract_openai_text(data)
                return text.strip() if self.strip_response else text

            raise SkipVendor(self.name, None, "request error")

        if self.schema == "anthropic":
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.max_tokens,
            }
            if self.extra_payload:
                payload.update(self.extra_payload)
            for attempt in range(1, max_attempts + 1):
                _wait_for_global_rate_limit(self.name)
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
                except requests.RequestException as exc:
                    status = getattr(exc.response, "status_code", None)
                    if status == 429:
                        _trigger_global_rate_limit_pause(self.name, status=429)
                    if attempt < max_attempts and self._is_retryable_exception(exc):
                        wait = self._retry_wait(attempt)
                        logging.warning(
                            "[%s] 请求异常，第 %d/%d 次重试前等待 %.1fs: %s",
                            self.name,
                            attempt,
                            max_attempts,
                            wait,
                            exc,
                        )
                        time.sleep(wait)
                        continue
                    raise SkipVendor(self.name, status, str(exc)) from None

                status = response.status_code
                if status in _TRANSIENT_HTTP_STATUS:
                    if status == 429:
                        _trigger_global_rate_limit_pause(self.name, status=429)
                    if attempt < max_attempts:
                        wait = self._retry_wait(attempt)
                        logging.warning(
                            "[%s] 命中 HTTP %s，第 %d/%d 次重试前等待 %.1fs",
                            self.name,
                            status,
                            attempt,
                            max_attempts,
                            wait,
                        )
                        time.sleep(wait)
                        continue
                    raise SkipVendor(self.name, status, body=response.text[:200])

                try:
                    response.raise_for_status()
                except requests.RequestException as exc:
                    status = getattr(exc.response, "status_code", None)
                    raise SkipVendor(self.name, status, str(exc), body=response.text[:200]) from None

                try:
                    data = response.json()
                except Exception as exc:
                    raise SkipVendor(self.name, status, f"invalid JSON: {exc}", body=response.text[:200]) from None

                parts = data.get("content", [])
                texts = [
                    part.get("text", "")
                    for part in parts
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                text = "\n".join(t for t in texts if t)
                return text.strip() if self.strip_response else text

            raise SkipVendor(self.name, None, "request error")

        raise RuntimeError(f"未知 schema: {self.schema}")


# ----------------------------------------------------------------------

def normalize_to_digit_series(text: str, n: int = 100) -> str:
    digits = re.findall(r"[0-9]", text or "")
    return ",".join(digits[:n])


def slugify(text: str, max_len: int = 40) -> str:
    cleaned = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fa5]+", "-", text).strip("-")
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip("-")
    cleaned = re.sub(r"^-+|-+$", "", cleaned)
    if not cleaned:
        cleaned = "q"
    return f"q-{cleaned}"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def now_iso_for_filename() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(":", "-")


def _clean_number(x: Any):
    try:
        value = float(x)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    except Exception:
        return x


def sanitize_for_json(obj: Any):
    try:
        import numpy as np  # type: ignore

        np_types = (np.integer, np.floating, np.bool_, np.ndarray)
    except Exception:  # pragma: no cover - numpy not installed
        np_types = tuple()

    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, float):
        return _clean_number(obj)
    if isinstance(obj, (int, str, bool)) or obj is None:
        return obj
    if np_types and isinstance(obj, np_types):  # pragma: no branch - depends on numpy
        try:
            import numpy as np  # type: ignore

            if isinstance(obj, np.ndarray):
                return sanitize_for_json(obj.tolist())
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return _clean_number(float(obj))
        except Exception:
            pass
    return str(obj)


def _num_or_none(x: Any) -> Optional[float]:
    try:
        value = float(x)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    except Exception:
        return None


def _round_or_none(x: Any, digits: int) -> Optional[float]:
    value = _num_or_none(x)
    if value is None:
        return None
    return round(value, digits)


def default_run_once(
    *,
    client: UnifiedClient,
    tester: check.DeepSeekSequenceTester,
    prompt: str,
    digits: int,
    temperature: float,
) -> Dict[str, Any]:
    logging.info("====== 开始：%s 生成 & 检验 ======", client.name)
    try:
        raw = client.generate(prompt, temperature=temperature)
    except SkipVendor as exc:
        logging.warning("[skip] %s", exc)
        summary = {
            "vendor": client.name,
            "skipped": True,
            "reason": f"HTTP {exc.status}" if exc.status is not None else "request error",
            "body": exc.body,
        }
        return {"sequence": "", "raw": "", "stats": {}, "summary": summary}

    seq = normalize_to_digit_series(raw, n=digits)
    if not seq:
        logging.warning("[%s] 规范化序列为空，跳过检验。原始输出长度=%d", client.name, len(raw or ""))
        summary = {
            "vendor": client.name,
            "skipped": True,
            "reason": "empty sequence",
            "raw_len": len(raw or ""),
            "raw_preview": str(raw or "")[:200],
        }
        return {"sequence": "", "raw": raw, "stats": {}, "summary": summary}

    logging.info("[%s] 规范化序列: %s", client.name, seq)

    stats = tester.hypothesis_test(prompt, seq, alpha=0.05, use_concurrent=True)

    abs_z_value = _round_or_none(stats.get("绝对Z统计量"), 6)
    token_log_dev_value = _round_or_none(stats.get("每token log偏差度"), 6)
    if abs_z_value is None:
        summary = {
            "vendor": client.name,
            "skipped": True,
            "reason": "invalid token distribution sample",
            "error": str(stats.get("检验结论") or "")[:240],
            "len": int(stats.get("序列长度") or 0),
            "failed_positions": int(stats.get("失败位置数") or 0),
        }
        logging.warning("[%s] 检验结果无效，已丢弃：%s", client.name, summary["error"])
        return {"sequence": seq, "raw": raw, "stats": stats, "summary": summary}

    summary = {
        "vendor": client.name,
        "len": int(stats.get("序列长度") or 0),
        "abs_Z": abs_z_value,
        "token_log_dev": token_log_dev_value,
    }
    logging.info("[%s] 摘要: %s", client.name, json.dumps(summary, ensure_ascii=False))
    print(f"[{client.name}] |Z|={summary['abs_Z']}, token_log_dev={summary['token_log_dev']}")
    return {"sequence": seq, "raw": raw, "stats": stats, "summary": summary}


def _build_tester(tester_conf: Any) -> check.DeepSeekSequenceTester:
    if hasattr(tester_conf, "hypothesis_test"):
        return tester_conf  # already an instance
    if not isinstance(tester_conf, MutableMapping):
        raise TypeError("tester configuration must be a mapping or DeepSeekSequenceTester instance")
    return check.DeepSeekSequenceTester(**tester_conf)  # type: ignore[arg-type]


def _build_clients(vendors: Sequence[Any], *, timeout: Optional[float]) -> List[UnifiedClient]:
    clients: List[UnifiedClient] = []
    for item in vendors:
        if hasattr(item, "generate"):
            clients.append(item)  # type: ignore[arg-type]
            continue
        if not isinstance(item, MutableMapping):
            raise TypeError("vendor configuration must be mappings or UnifiedClient instances")
        clients.append(UnifiedClient(item, timeout=timeout))
    return clients


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def run_tests(config: Any) -> List[str]:
    """Run sequence tests based on the supplied configuration.

    The configuration can be a single mapping describing one test suite, a list of
    suites, or a mapping containing a ``tests`` key with a list of suites. Each
    suite must provide at least ``questions``, ``runs_per_question``, ``digits``,
    ``temperature``, ``tester`` (configuration or instance), and ``vendors``.
    Optional keys:
        ``result_dir``: output directory (default ``<data-dir>/qtest/result/json``)
        ``top_logprobs``: stored in payload metadata when provided
        ``vendor_max_workers``: concurrent workers for vendor requests in each run
        ``max_inflight_ref_requests``: max inflight reference-distribution requests (vendor workers auto-capped)
        ``align_tester_temperature``: align tester.temperature with generation temperature (default ``True``)
        ``payload``: additional key/value pairs merged into each payload
        ``run_once``: callable overriding :func:`default_run_once`
    """

    if isinstance(config, MutableMapping) and "tests" in config:
        outputs: List[str] = []
        for sub in _as_list(config["tests"]):
            outputs.extend(run_tests(sub))
        return outputs

    if isinstance(config, Sequence) and not isinstance(config, (str, bytes, bytearray)):
        outputs: List[str] = []
        for sub in config:
            outputs.extend(run_tests(sub))
        return outputs

    if not isinstance(config, MutableMapping):
        raise TypeError("run_tests expects a mapping, a list of mappings, or a mapping with 'tests'")

    questions = list(config.get("questions", []))
    runs_per_question = int(config.get("runs_per_question", 1))
    digits = int(config.get("digits", 100))
    temperature = float(config.get("temperature", 0.6))
    top_logprobs = config.get("top_logprobs")
    vendor_max_workers = max(1, int(config.get("vendor_max_workers", 1)))
    max_inflight_ref_requests = max(1, int(config.get("max_inflight_ref_requests", _DEFAULT_MAX_INFLIGHT_REF_REQUESTS)))
    align_tester_temperature = bool(config.get("align_tester_temperature", True))
    result_dir = config.get("result_dir", _DEFAULT_RESULT_DIR)
    payload_overrides = config.get("payload", {})

    if not questions:
        from .questions import build_questions
        questions = build_questions()
        logging.info("未提供 questions，已自动生成 %d 条随机示例问题。", len(questions))

    if not questions:
        logging.warning("未提供任何问题，跳过执行。")
        return []

    tester = _build_tester(config.get("tester", {}))
    if align_tester_temperature and hasattr(tester, "temperature"):
        try:
            tester_temperature = float(getattr(tester, "temperature"))
        except Exception:
            tester_temperature = None
        if tester_temperature is not None and not math.isclose(tester_temperature, temperature, rel_tol=0.0, abs_tol=1e-12):
            logging.info(
                "对齐 tester.temperature: %.6f -> %.6f（保持与生成温度一致）",
                tester_temperature,
                temperature,
            )
            setattr(tester, "temperature", float(temperature))

    timeout = getattr(tester, "timeout_sec", None)
    clients = _build_clients(config.get("vendors", []), timeout=timeout)
    if not clients:
        raise ValueError("no vendor clients configured")

    tester_workers = max(1, int(getattr(tester, "max_workers", 1) or 1))
    max_vendor_by_ref = max(1, max_inflight_ref_requests // tester_workers)
    effective_vendor_max_workers = max(1, min(vendor_max_workers, max_vendor_by_ref))
    if effective_vendor_max_workers < vendor_max_workers:
        logging.info(
            "供应商并发自动下调: %d -> %d（tester.max_workers=%d, max_inflight_ref_requests=%d）",
            vendor_max_workers,
            effective_vendor_max_workers,
            tester_workers,
            max_inflight_ref_requests,
        )

    run_once_callable = config.get("run_once") or default_run_once

    ensure_dir(result_dir)

    output_paths: List[str] = []
    for q_idx, question in enumerate(questions, start=1):
        q_slug = slugify(question)
        for run_idx in range(1, runs_per_question + 1):
            logging.info(
                "=== 问题 %d/%d：%s | 运行 %d/%d ===",
                q_idx,
                len(questions),
                question,
                run_idx,
                runs_per_question,
            )

            all_out: Dict[str, Any] = {}
            vendor_details: Dict[str, Any] = {}
            per_vendor_result: Dict[str, Dict[str, Any]] = {}
            per_vendor_error: Dict[str, str] = {}

            def _run_single_vendor(client: UnifiedClient) -> Dict[str, Any]:
                return run_once_callable(
                    client=client,
                    tester=tester,
                    prompt=question,
                    digits=digits,
                    temperature=temperature,
                )

            if effective_vendor_max_workers <= 1 or len(clients) <= 1:
                for client in clients:
                    try:
                        per_vendor_result[client.name] = _run_single_vendor(client)
                    except Exception as exc:  # pragma: no cover - defensive logging
                        logging.error("vendor %s 处理失败：%s", getattr(client, "name", "<unknown>"), exc)
                        per_vendor_error[getattr(client, "name", "<unknown>")] = str(exc)
            else:
                workers = min(effective_vendor_max_workers, len(clients))
                logging.info("启用供应商并发 | workers=%d | vendors=%d", workers, len(clients))
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    future_map = {
                        executor.submit(_run_single_vendor, client): client
                        for client in clients
                    }
                    for future in concurrent.futures.as_completed(future_map):
                        client = future_map[future]
                        try:
                            per_vendor_result[client.name] = future.result()
                        except Exception as exc:  # pragma: no cover - defensive logging
                            logging.error("vendor %s 处理失败：%s", client.name, exc)
                            per_vendor_error[client.name] = str(exc)

            # 保持输出顺序与配置顺序一致，避免下游比对抖动。
            for client in clients:
                if client.name in per_vendor_result:
                    result = per_vendor_result[client.name]
                    all_out[client.name] = result["summary"]
                    vendor_details[client.name] = {
                        "sequence": result.get("sequence", ""),
                        "raw": result.get("raw", ""),
                        "stats": result.get("stats", {}),
                    }
                else:
                    all_out[client.name] = {"error": per_vendor_error.get(client.name, "unknown error")}

            timestamp_for_file = now_iso_for_filename()
            payload: Dict[str, Any] = {
                "question": question,
                "question_slug": q_slug,
                "run_index": run_idx,
                "timestamp_utc": timestamp_for_file,
                "digits": digits,
                "temperature": temperature,
                "vendors": [client.name for client in clients],
                "vendor_models": {client.name: client.model for client in clients},
                "vendor_meta": {
                    client.name: {
                        "model": client.model,
                        "schema": client.schema,
                        "base_url": client.base_url,
                        "path": client.path,
                    }
                    for client in clients
                },
                "summaries": all_out,
                "details": vendor_details,
            }
            if top_logprobs is not None:
                payload["top_logprobs"] = top_logprobs
            if payload_overrides:
                payload.update(payload_overrides)

            filename = f"{q_slug}_{timestamp_for_file}_run{run_idx}.json"
            outpath = os.path.join(result_dir, filename)
            sanitized = sanitize_for_json(payload)
            with open(outpath, "w", encoding="utf-8") as f:
                json.dump(sanitized, f, ensure_ascii=False, indent=2)

            print("\n=== RESULT SAVED ===")
            print(outpath)
            output_paths.append(outpath)

    print("\n全部问题/运行已完成。")
    return output_paths
