# Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Requirement: Any integration or derivative work must explicitly attribute
# Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
# documentation or user interface, as detailed in the NOTICE file.

"""LLM 调用的限流感知重试。

内部/共享 LLM 网关普遍存在 QPM 限制，直接调用遇到 429 时异常上抛会导致
整个扫描任务失败。此模块提供同步/异步两个重试包装：

- 识别限流类错误（HTTP 429、报错信息含 rate limit / too many requests 等标记）；
- 服务端返回 Retry-After 时优先遵循（上限 60s）；
- 否则按 8s/16s/32s（上限 60s）退避；
- 非限流错误保持短指数退避（1s 起步，上限 8s）；
- 默认最多尝试 5 次，耗尽后抛出最后一次异常。
"""

import asyncio
import time

from mcp_scan.utils.loging import logger

# 限流错误的消息标记（不同网关措辞不一致）
_RATE_LIMIT_MARKERS = (
    "rate limit",
    "rate_limit",
    "ratelimit",
    "too many requests",
    "quota exceeded",
    "quota_exceeded",
    "resource_exhausted",
    "resource exhausted",
    "429",
)

# 限流退避表（无 Retry-After 时使用），上限 60s
_RATE_LIMIT_BACKOFF = (8.0, 16.0, 32.0, 60.0, 60.0)

MAX_TRIALS = 5


def is_rate_limit_error(exc: BaseException) -> bool:
    """判断异常是否为限流类错误（429 / 配额耗尽）。"""
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    message = str(exc).lower()
    return any(marker in message for marker in _RATE_LIMIT_MARKERS)


def retry_after_seconds(exc: BaseException) -> float | None:
    """从异常携带的响应头中提取 Retry-After（秒），取不到返回 None。"""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    try:
        raw = headers.get("retry-after")
    except Exception:
        return None
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def backoff_delay(attempt: int, rate_limited: bool, retry_after: float | None) -> float:
    """计算第 attempt 次（从 0 开始）失败后的等待秒数。"""
    if rate_limited:
        if retry_after and retry_after > 0:
            return min(retry_after, 60.0)
        return _RATE_LIMIT_BACKOFF[min(attempt, len(_RATE_LIMIT_BACKOFF) - 1)]
    return min(1.0 * (2**attempt), 8.0)


def call_with_retry(func, *, what: str = "LLM call", max_trials: int = MAX_TRIALS):
    """同步执行 func()，限流感知重试，重试耗尽后抛出最后一次异常。"""
    for attempt in range(max_trials):
        try:
            return func()
        except Exception as exc:
            if attempt >= max_trials - 1:
                raise
            rate_limited = is_rate_limit_error(exc)
            retry_after = retry_after_seconds(exc) if rate_limited else None
            delay = backoff_delay(attempt, rate_limited, retry_after)
            logger.error(
                f"{what} failed (trial {attempt + 1}/{max_trials}): "
                f"{type(exc).__name__}: {exc}; backoff {delay:.1f}s"
                + (" (rate-limited)" if rate_limited else "")
            )
            time.sleep(delay)
    raise RuntimeError("unreachable")  # pragma: no cover


async def acall_with_retry(func, *, what: str = "LLM call", max_trials: int = MAX_TRIALS):
    """异步执行 await func()，限流感知重试，重试耗尽后抛出最后一次异常。"""
    for attempt in range(max_trials):
        try:
            return await func()
        except Exception as exc:
            if attempt >= max_trials - 1:
                raise
            rate_limited = is_rate_limit_error(exc)
            retry_after = retry_after_seconds(exc) if rate_limited else None
            delay = backoff_delay(attempt, rate_limited, retry_after)
            logger.error(
                f"{what} failed (trial {attempt + 1}/{max_trials}): "
                f"{type(exc).__name__}: {exc}; backoff {delay:.1f}s"
                + (" (rate-limited)" if rate_limited else "")
            )
            await asyncio.sleep(delay)
    raise RuntimeError("unreachable")  # pragma: no cover
