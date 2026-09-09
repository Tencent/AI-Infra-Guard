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

import time
import asyncio
import threading
from openai import OpenAI, AsyncOpenAI
from .base import BaseLLM

# 限流相关错误关键字（不依赖 openai 具体异常类型，兼容各类 OpenAI 兼容网关）
RATE_LIMIT_MARKERS = (
    "rate limit",
    "rate_limit",
    "ratelimit",
    "too many requests",
    "quota",
    "requests per minute",
    "requests per second",
    "status code: 429",
    "error code: 429",
    "code 429",
    "http 429",
)


def _is_rate_limit_error(exc: Exception) -> bool:
    """判断异常是否为限流/配额类错误（含 429 状态码与常见限流文案）

    注意：刻意不做裸子串 "429" 匹配，避免把恰好含 429 的请求 ID / 错误码误判为限流。
    """
    msg = str(exc).lower()
    if any(marker in msg for marker in RATE_LIMIT_MARKERS):
        return True
    # 独立数字 429（前后是词边界以外的字符），兼容 "429 Too Many Requests" 这类文案；
    # (?<![0-9a-z_]) 排除 req_429ab3c / 4290ms 这类数字串中的 429
    import re

    return bool(re.search(r"(?<![0-9a-z_])429(?![0-9a-z_])", msg))


def _retry_after_seconds(exc: Exception, default: float) -> float:
    """从异常中提取服务端建议的重试等待秒数，取不到时返回 default

    openai SDK 1.x/3.x 会把原始响应放在异常的 `response` 属性上
    （APIStatusError 系），`Retry-After` 位于 `exc.response.headers`；
    部分网关会把建议等待值放在异常 `retry_after` 属性或消息文本里，一并兼容。
    """
    # 1) openai.APIStatusError: exc.response.headers["retry-after"]
    response = getattr(exc, "response", None)
    if response is not None:
        headers = getattr(response, "headers", None)
        if headers is not None:
            lowered = {}
            try:
                for key, value in headers.items():
                    lowered[str(key).lower()] = value
            except Exception:
                lowered = {}
            for key in ("retry-after", "retry-after-ms", "x-ratelimit-reset-requests"):
                raw = lowered.get(key)
                if raw is None:
                    continue
                try:
                    value = float(raw)
                    if key == "retry-after-ms":
                        value /= 1000.0
                    if 0 < value <= 600:
                        return value
                except (TypeError, ValueError):
                    continue
    # 2) 异常自带 retry_after 属性（部分网关/SDK 行为）
    try:
        retry_after = getattr(exc, "retry_after", None)
        if retry_after:
            return float(retry_after)
    except Exception:
        pass
    # 3) 消息文本中的 "retry after N seconds" 提示
    import re

    m = re.search(r"retry\s+(?:after|in)\s+(\d+(?:\.\d+)?)", str(exc), re.IGNORECASE)
    if m:
        value = float(m.group(1))
        if 0 < value <= 600:
            return value
    return default


class OpenaiAlikeModel(BaseLLM):
    """自定义模型，用于支持OpenAI API Alike Model"""
    max_trial = 5
    base_wait_seconds = 1.0
    max_wait_seconds = 60.0
    # 限流专用退避：QPM 窗口通常为 60s，短退避会在窗口内反复撞墙浪费配额，
    # 故限流场景以 8s 起步并指数递增（8/16/32/60），普通错误仍用 base_wait_seconds
    rate_limit_base_wait_seconds = 8.0

    def __init__(self, model_name: str, base_url: str, api_key: str, max_concurrent: int, *args, **kwargs):
        super().__init__(model_name, base_url, api_key, max_concurrent, *args, **kwargs)
        # 连续限流失败计数：与 RedTeamer 熔断器共享（后者通过 model_callback.__self__ 读取），
        # 多线程/协程并发递增时用锁保护；属性显式初始化，绕过 __init__ 构造的实例则惰性创建
        self._consecutive_rate_limit_failures = 0
        self._rate_limit_lock = threading.Lock()
        self.load_model()

    def _get_rate_limit_lock(self) -> threading.Lock:
        """获取计数器锁（绕过 __init__ 构造的实例上惰性创建）"""
        lock = getattr(self, "_rate_limit_lock", None)
        if lock is None:
            lock = threading.Lock()
            self._rate_limit_lock = lock
        return lock

    def note_rate_limit_failure(self):
        """记录一次限流失败（供熔断器与重试逻辑共同递增，线程安全）"""
        with self._get_rate_limit_lock():
            self._consecutive_rate_limit_failures = getattr(
                self, "_consecutive_rate_limit_failures", 0
            ) + 1
            return self._consecutive_rate_limit_failures

    def get_consecutive_rate_limit_failures(self) -> int:
        """读取连续限流失败次数（供 RedTeamer 熔断器判断）"""
        with self._get_rate_limit_lock():
            return getattr(self, "_consecutive_rate_limit_failures", 0)

    def reset_rate_limit_failures(self):
        """成功响应后清零连续限流失败计数"""
        with self._get_rate_limit_lock():
            self._consecutive_rate_limit_failures = 0
    
    def load_model(self):
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        self.async_client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        self.default_params = {
            "reasoning_effort": "low",
            "frequency_penalty": 1.0,
            "max_completion_tokens": 2048
        }
        return self.client
    
    def test_model_connection(self):
        """
        测试模型是否连通
        
        返回:
            bool: True 表示连通，False 表示连接失败
            str: 返回的响应内容或错误信息
        """
        current_params = self.default_params.copy()
        param_keys = list(current_params.keys())
        for i in range(len(param_keys) + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": "only return 1"}],
                    **current_params
                )
                # 如果成功，返回成功的信息和使用的参数
                self.default_params = current_params.copy()
                return True, response.choices[0].message.content
            except Exception as e:
                last_error = str(e)
                # 如果还有参数可以移除，移除下一个参数
                if i < len(param_keys):
                    param_to_remove = param_keys[i]
                    current_params.pop(param_to_remove, None)
                # 否则继续循环（最后一次尝试无参数）

        # 所有尝试都失败
        return False, last_error

    def generate(self, prompt: str = None, messages: list = None) -> str:
        for i in range(self.max_trial):
            try:
                if prompt:
                    _messages = [{"role": "user", "content": prompt}]
                elif messages:
                    _messages = messages
                else:
                    raise ValueError("prompt and messages cannot both be empty")
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=_messages,
                    **self.default_params
                )
                content = response.choices[0].message.content
                if not isinstance(content, str):
                    raise ValueError("The response is not a string")
                elif not content:
                    raise ValueError("The response is empty")
                self.reset_rate_limit_failures()
                return content
            except Exception as e:
                if _is_rate_limit_error(e):
                    self.note_rate_limit_failure()
                    fallback = max(
                        self.rate_limit_base_wait_seconds,
                        self.base_wait_seconds,
                    ) * (2 ** min(i, 2))
                    wait_time = min(
                        _retry_after_seconds(e, fallback),
                        self.max_wait_seconds,
                    )
                else:
                    wait_time = self.base_wait_seconds * (2 ** i)
                time.sleep(wait_time)
        return ""
    
    async def a_generate(self, prompt: str = None, messages: list = None) -> str:
        async with self.semaphore:
            for i in range(self.max_trial):
                try:
                    if prompt:
                        _messages = [{"role": "user", "content": prompt}]
                    elif messages:
                        _messages = messages
                    else:
                        raise ValueError("prompt and messages cannot both be empty")
                    
                    response = await self.async_client.chat.completions.create(
                        model=self.model_name,
                        messages=_messages,
                        **self.default_params
                    )
                    content = response.choices[0].message.content
                    if not isinstance(content, str):
                        raise ValueError("The response is not a string")
                    elif not content:
                        raise ValueError("The response is empty")
                    self.reset_rate_limit_failures()
                    return content
                except Exception as e:
                    if _is_rate_limit_error(e):
                        self.note_rate_limit_failure()
                        fallback = max(
                            self.rate_limit_base_wait_seconds,
                            self.base_wait_seconds,
                        ) * (2 ** min(i, 2))
                        wait_time = min(
                            _retry_after_seconds(e, fallback),
                            self.max_wait_seconds,
                        )
                    else:
                        wait_time = self.base_wait_seconds * (2 ** i)
                    await asyncio.sleep(wait_time)
            return ""
    
    def get_model_name(self):
        return self.model_name