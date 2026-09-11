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

import asyncio
import time

import litellm
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    BadRequestError,
    Timeout,
)

from agent_scan.utils.logging import logger

# Error prefix constant for consistent error detection across modules
LLM_ERROR_PREFIX = "[LLM Error:"


def to_litellm_params(model: str, base_url: str | None) -> tuple[str, str | None]:
    """Map the configured (model, base_url) onto LiteLLM's routing.

    - base_url set (the default, e.g. OpenRouter or any OpenAI-compatible
      gateway): route the request as a custom OpenAI-compatible endpoint by
      prefixing the model with ``openai/`` and passing base_url as ``api_base``.
      The wire request is identical to the previous ``openai.OpenAI(base_url)``
      call, so existing configurations keep working unchanged.
    - base_url empty: pass the model through untouched so LiteLLM routes to a
      provider natively (e.g. ``anthropic/claude-...``, ``bedrock/...``,
      ``gemini/...``), which resolves credentials from that provider's own env
      vars and needs no gateway or proxy.
    """
    if base_url:
        litellm_model = model if model.startswith("openai/") else f"openai/{model}"
        return litellm_model, base_url
    return model, None


def is_llm_error_response(response: str) -> bool:
    return isinstance(response, str) and response.startswith(LLM_ERROR_PREFIX)


def format_llm_error_message(language: str, zh_message: str, en_message: str) -> str:
    message = en_message if language == "en" else zh_message
    return f"{LLM_ERROR_PREFIX} {message}]"


class LLM:
    def __init__(self, model, api_key, base_url):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    async def chat_async(self, message: list[dict], language: str = "zh") -> str:
        """Non-blocking wrapper around :meth:`chat` for use inside async contexts.

        Runs the synchronous ``litellm.completion`` call in a thread-pool
        executor via :func:`asyncio.to_thread`, so the event loop is free to schedule
        other coroutines (e.g. parallel skill workers) while waiting for the
        LLM response.

        Args:
            message: Conversation history in OpenAI chat format.
            language: Language for error messages ("zh" or "en").

        Returns:
            The model's response text.
        """
        return await asyncio.to_thread(self.chat, message, False, language)

    def chat(self, message: list[dict], p=False, language: str = "zh"):
        """Send a chat request to the LLM.

        Args:
            message: Conversation history in OpenAI chat format.
            p: Whether to print the response.
            language: Language for error messages ("zh" or "en").

        Returns:
            The model's response text, or an error string prefixed with LLM_ERROR_PREFIX.
        """
        retry = 0
        while True:
            ret = ''
            try:
                for word in self.chat_stream(message):
                    ret += word
                if ret != '':
                    break
                else:
                    # Empty response: network jitter or model occasionally returns empty, can retry
                    retry += 1
                    logger.error(f'LLM chat error (empty response), retry {retry}')
                    time.sleep(1.3)
                    if retry > 3:
                        logger.error('LLM chat error, retry 3 times, exit')
                        return format_llm_error_message(
                            language,
                            "连接LLM失败，已重试3次，模型输出为空，请等待1分钟后再试",
                            "Failed to connect to LLM, retried 3 times, model output is empty, please try again after 1 minute",
                        )
                    continue
            except BadRequestError as e:
                # 400 error (e.g. DataInspectionFailed): content issue, retry is meaningless, return immediately
                error_msg = str(e)
                logger.warning(f"LLM BadRequestError (400), no retry: {error_msg}")
                return format_llm_error_message(
                    language,
                    "输入内容触发安全过滤 (400)",
                    "Input content triggered safety filter (400)",
                )
            except (APIConnectionError, Timeout) as e:
                # Network/timeout error: can retry
                retry += 1
                logger.warning(f'LLM connection/timeout error, retry {retry}: {e}')
                if retry > 5:
                    logger.error('LLM connection error, retry 5 times, exit')
                    return format_llm_error_message(
                        language,
                        "无法连接到LLM服务，已重试5次",
                        "Unable to connect to LLM service, retried 5 times",
                    )
                time.sleep(2)
                continue
            except APIError as e:
                # Other API errors (5xx, etc.): can retry
                retry += 1
                logger.warning(f'LLM API error, retry {retry}: {e}')
                if retry > 3:
                    logger.error('LLM API error, retry 3 times, exit')
                    return format_llm_error_message(
                        language,
                        "无法连接到LLM服务，已重试3次",
                        "Unable to connect to LLM service, retried 3 times",
                    )
                time.sleep(1)
                continue
            except Exception as e:
                # Unexpected exception: return immediately, do not retry
                logger.error(f'Unexpected LLM error: {e}', exc_info=True)
                return format_llm_error_message(
                    language,
                    f"发生未预期的错误 - {str(e)[:100]}",
                    f"Unexpected error occurred - {str(e)[:100]}",
                )

        if p:
            print(ret)
        return ret


    def chat_stream(self, message: list[dict]):
        """Stream chat completions from the LLM.

        Exceptions from the underlying API call propagate to chat() for
        centralized handling and retry logic. Only unexpected (non-OpenAI)
        exceptions are logged here before re-raising.

        Args:
            message: Conversation history in OpenAI chat format.

        Yields:
            Content chunks from the model response.

        Raises:
            litellm.BadRequestError: Content triggered safety filter (400).
            litellm.APIConnectionError: Network connection failed.
            litellm.Timeout: Request timed out.
            litellm.APIError: Other API errors (5xx, etc.).
        """
        litellm_model, api_base = to_litellm_params(self.model, self.base_url)
        try:
            response = litellm.completion(
                model=litellm_model,
                messages=message,
                stream=True,
                api_key=self.api_key or None,
                api_base=api_base,
                timeout=60,
                # Silently drop generation params a given provider does not
                # accept, so one config works across OpenAI, Anthropic, Gemini,
                # Bedrock, etc. instead of 400-ing on provider-specific kwargs.
                drop_params=True,
            )

            for chunk in response:
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
                    yield content

        except (BadRequestError, APIConnectionError, Timeout, APIError):
            # LiteLLM exceptions propagate directly to chat() for handling
            raise
        except Exception as e:
            # Log unexpected (non-LiteLLM) exceptions before re-raising
            logger.error(f'Unexpected error in chat_stream: {e}', exc_info=True)
            raise
