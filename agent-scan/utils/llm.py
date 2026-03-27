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

import openai
from typing import List
from utils.logging import logger

# Error prefix constant for consistent error detection across modules
LLM_ERROR_PREFIX = "[LLM Error:"


class LLM:
    def __init__(self, model, api_key, base_url):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=60)
        self.temperature = 0.7

    async def chat_async(self, message: List[dict], language: str = "zh") -> str:
        """Non-blocking wrapper around :meth:`chat` for use inside async contexts.

        Runs the synchronous ``openai.OpenAI`` call in a thread-pool executor
        via :func:`asyncio.to_thread`, so the event loop is free to schedule
        other coroutines (e.g. parallel skill workers) while waiting for the
        LLM response.

        Args:
            message: Conversation history in OpenAI chat format.
            language: Language for error messages ("zh" or "en").

        Returns:
            The model's response text.
        """
        return await asyncio.to_thread(self.chat, message, False, language)

    def chat(self, message: List[dict], p=False, language: str = "zh"):
        """Send a chat request to the LLM.

        Args:
            message: Conversation history in OpenAI chat format.
            p: Whether to print the response.
            language: Language for error messages ("zh" or "en").

        Returns:
            The model's response text, or an error string prefixed with LLM_ERROR_PREFIX.
        """
        ret = ''
        retry = 0
        while True:
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
                        if language == "en":
                            return f'{LLM_ERROR_PREFIX} Failed to connect to LLM, retried 3 times, model output is empty, please try again after 1 minute]'
                        return f'{LLM_ERROR_PREFIX} 连接LLM失败，已重试3次，模型输出为空，请等待1分钟后再试]'
            except openai.BadRequestError as e:
                # 400 error (e.g. DataInspectionFailed): content issue, retry is meaningless, return immediately
                error_msg = str(e)
                logger.warning(f"LLM BadRequestError (400), no retry: {error_msg}")
                if language == "en":
                    return f'{LLM_ERROR_PREFIX} Input content triggered safety filter (400)]'
                return f'{LLM_ERROR_PREFIX} 输入内容触发安全过滤 (400)]'
            except (openai.APIConnectionError, openai.APITimeoutError) as e:
                # Network/timeout error: can retry
                retry += 1
                logger.warning(f'LLM connection/timeout error, retry {retry}: {e}')
                if retry > 5:
                    logger.error('LLM connection error, retry 5 times, exit')
                    if language == "en":
                        return f'{LLM_ERROR_PREFIX} Unable to connect to LLM service, retried 5 times]'
                    return f'{LLM_ERROR_PREFIX} 无法连接到LLM服务，已重试5次]'
                time.sleep(2)
                continue
            except openai.APIError as e:
                # Other API errors (5xx, etc.): can retry
                retry += 1
                logger.warning(f'LLM API error, retry {retry}: {e}')
                if retry > 3:
                    logger.error('LLM API error, retry 3 times, exit')
                    if language == "en":
                        return f'{LLM_ERROR_PREFIX} Unable to connect to LLM service, retried 3 times]'
                    return f'{LLM_ERROR_PREFIX} 无法连接到LLM服务，已重试3次]'
                time.sleep(1)
                continue
            except Exception as e:
                # Unexpected exception: return immediately, do not retry
                logger.error(f'Unexpected LLM error: {e}', exc_info=True)
                if language == "en":
                    return f'{LLM_ERROR_PREFIX} Unexpected error occurred - {str(e)[:100]}]'
                return f'{LLM_ERROR_PREFIX} 发生未预期的错误 - {str(e)[:100]}]'

        if p:
            print(ret)
        return ret


    def chat_stream(self, message: List[dict]):
        """Stream chat completions from the LLM.

        Exceptions from the underlying API call propagate to chat() for
        centralized handling and retry logic. Only unexpected (non-OpenAI)
        exceptions are logged here before re-raising.

        Args:
            message: Conversation history in OpenAI chat format.

        Yields:
            Content chunks from the model response.

        Raises:
            openai.BadRequestError: Content triggered safety filter (400).
            openai.APIConnectionError: Network connection failed.
            openai.APITimeoutError: Request timed out.
            openai.APIError: Other API errors (5xx, etc.).
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=message,
                temperature=self.temperature,
                stream=True
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

        except (openai.BadRequestError, openai.APIConnectionError,
                openai.APITimeoutError, openai.APIError):
            # OpenAI exceptions propagate directly to chat() for handling
            raise
        except Exception as e:
            # Log unexpected (non-OpenAI) exceptions before re-raising
            logger.error(f'Unexpected error in chat_stream: {e}', exc_info=True)
            raise
