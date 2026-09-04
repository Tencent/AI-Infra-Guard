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
from openai import OpenAI, AsyncOpenAI
from .base import BaseLLM

# 限流相关错误关键字（不依赖 openai 具体异常类型，兼容各类 OpenAI 兼容网关）
RATE_LIMIT_MARKERS = ("rate limit", "rate_limit", "429", "quota", "too many requests", "qps", "qpm")


def _is_rate_limit_error(exc: Exception) -> bool:
    """判断异常是否为限流/配额类错误（含 429 状态码与常见限流文案）"""
    msg = str(exc).lower()
    return any(marker in msg for marker in RATE_LIMIT_MARKERS)


def _retry_after_seconds(exc: Exception, default: float) -> float:
    """从异常中提取 Retry-After 提示值，失败时返回默认值"""
    try:
        retry_after = getattr(exc, "retry_after", None)
        if retry_after:
            return float(retry_after)
    except Exception:
        pass
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
        self.load_model()
    
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
                self._consecutive_rate_limit_failures = 0
                return content
            except Exception as e:
                if _is_rate_limit_error(e):
                    self._consecutive_rate_limit_failures = getattr(
                        self, "_consecutive_rate_limit_failures", 0
                    ) + 1
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
                    self._consecutive_rate_limit_failures = 0
                    return content
                except Exception as e:
                    if _is_rate_limit_error(e):
                        self._consecutive_rate_limit_failures = getattr(
                            self, "_consecutive_rate_limit_failures", 0
                        ) + 1
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