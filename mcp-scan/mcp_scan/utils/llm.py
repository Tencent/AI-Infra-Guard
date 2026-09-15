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
from typing import Any

import litellm

from mcp_scan.utils.loging import logger


def to_litellm_params(model: str, base_url: str | None) -> tuple[str, str | None]:
    """Map the configured (model, base_url) onto LiteLLM's routing.

    - base_url set (the default, e.g. OpenRouter or any OpenAI-compatible
      gateway): route as a custom OpenAI-compatible endpoint by prefixing the
      model with ``openai/`` and passing base_url as ``api_base``. The wire
      request is identical to the previous ``openai.OpenAI(base_url)`` call, so
      existing configurations keep working unchanged.
    - base_url empty: pass the model through so LiteLLM routes to a provider
      natively (e.g. ``anthropic/claude-...``, ``bedrock/...``), resolving
      credentials from that provider's own env vars with no gateway or proxy.
    """
    if base_url:
        litellm_model = model if model.startswith("openai/") else f"openai/{model}"
        return litellm_model, base_url
    return model, None


class LLM:
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        context_window: int | None = None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        # 用于估算压缩阈值，不依赖接口动态返回模型规格。
        self.context_window = context_window

    def chat(self, message: list[dict], p=False, ret_usage=False) -> str | tuple[str, dict]:
        ret = ""
        usage = None
        retry = 0

        while True:
            ret, usage = self.chat_stream(message)
            if ret != "":
                break
            else:
                retry += 1
                logger.error(f"LLM chat error, retry {retry}")
                time.sleep(1.3)
                if retry > 5:
                    logger.error("LLM chat error, retry 5 times, exit")
                    ret = "连接LLM失败，已重试5次，模型输出为空,请等待1分钟后再试"
                    break
        if p:
            print(ret)

        if ret_usage:
            return ret, usage
        return ret

    def chat_stream(self, message: list[dict]) -> tuple[str, dict]:
        litellm_model, api_base = to_litellm_params(self.model, self.base_url)
        response = litellm.completion(
            model=litellm_model,
            messages=message,
            stream=True,
            # usage 一般在流式结束时返回，前面的 chunk 通常为空。
            stream_options={"include_usage": True},
            api_key=self.api_key or None,
            api_base=api_base,
            timeout=60,
            # Drop provider-unsupported generation params so one config works
            # across OpenAI, Anthropic, Gemini, Bedrock, etc.
            drop_params=True,
        )

        ret = ""
        usage = None

        for chunk in response:
            _usage = getattr(chunk, "usage", None)
            if _usage:
                usage = self._normalize_usage(_usage)

            choices = getattr(chunk, "choices", None)

            # Ensure choices is a non-empty list
            if not isinstance(choices, list) or not choices:
                continue
            choice = choices[0]

            delta = getattr(choice, "delta", None)
            if not delta:
                continue

            content = getattr(delta, "content", None)
            if content:
                ret += content

        return ret, usage

    def _normalize_usage(self, usage) -> dict | None:
        if not usage:
            return None

        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }


class _LiteLLMAsyncCompletions:
    def __init__(self, api_key: str, base_url: str | None, timeout: int):
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout

    async def create(self, model: str, messages: list[dict], **kwargs) -> Any:
        litellm_model, api_base = to_litellm_params(model, self._base_url)
        params = {
            "model": litellm_model,
            "messages": messages,
            "api_key": self._api_key or None,
            "api_base": api_base,
            "timeout": self._timeout,
            # Drop provider-unsupported generation params so one config works
            # across OpenAI, Anthropic, Gemini, Bedrock, etc.
            "drop_params": True,
        }
        params.update(kwargs)
        return await litellm.acompletion(**params)


class _LiteLLMAsyncChat:
    def __init__(self, api_key: str, base_url: str | None, timeout: int):
        self.completions = _LiteLLMAsyncCompletions(api_key, base_url, timeout)


class LiteLLMAsyncClient:
    """Async LiteLLM client exposing the subset of the OpenAI ``AsyncClient``
    surface the red-team agents use (``chat.completions.create``), so their
    calls route through LiteLLM with no other changes.

    base_url is applied here (see :func:`to_litellm_params`), so callers keep
    passing just ``model`` and ``messages`` exactly as before. Responses have
    the same OpenAI shape (``choices[0].message.content``), so downstream
    parsing is unchanged.
    """

    def __init__(self, api_key: str, base_url: str | None = None, timeout: int = 90):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.chat = _LiteLLMAsyncChat(api_key, base_url, timeout)
