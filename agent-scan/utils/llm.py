import asyncio
import time

import openai
from typing import List
from utils.logging import logger


class LLM:
    def __init__(self, model, api_key, base_url):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=60)
        self.temperature = 0.7

    async def chat_async(self, message: List[dict]) -> str:
        """Non-blocking wrapper around :meth:`chat` for use inside async contexts.

        Runs the synchronous ``openai.OpenAI`` call in a thread-pool executor
        via :func:`asyncio.to_thread`, so the event loop is free to schedule
        other coroutines (e.g. parallel skill workers) while waiting for the
        LLM response.

        Args:
            message: Conversation history in OpenAI chat format.

        Returns:
            The model's response text.
        """
        return await asyncio.to_thread(self.chat, message)

    def chat(self, message: List[dict], p=False):
        ret = ''
        retry = 0
        while True:
            try:
                for word in self.chat_stream(message):
                    ret += word
                if ret != '':
                    break
                else:
                    # 空响应：网络抖动或模型偶发返回空，可重试
                    retry += 1
                    logger.error(f'LLM chat error (empty response), retry {retry}')
                    time.sleep(1.3)
                    if retry > 3:
                        logger.error('LLM chat error, retry 3 times, exit')
                        return '连接LLM失败，已重试3次，模型输出为空,请等待1分钟后再试'
            except openai.BadRequestError as e:
                # 400 错误（如 DataInspectionFailed）：内容问题，重试无意义，立即返回
                error_msg = str(e)
                logger.warning(f"LLM BadRequestError (400), no retry: {error_msg}")
                return f'[LLM Error: 输入内容触发安全过滤 (400)]'
            except (openai.APIConnectionError, openai.APITimeoutError) as e:
                # 网络/超时错误：可重试
                retry += 1
                logger.warning(f'LLM connection/timeout error, retry {retry}: {e}')
                if retry > 5:
                    logger.error('LLM connection error, retry 5 times, exit')
                    return '[LLM Error: 无法连接到LLM服务，已重试5次]'
                time.sleep(2)
                continue
            except openai.APIError as e:
                # 其他 API 错误（5xx 等）：可重试
                retry += 1
                logger.warning(f'LLM API error, retry {retry}: {e}')
                if retry > 3:
                    logger.error('LLM API error, retry 3 times, exit')
                    return '[LLM Error: 无法连接到LLM服务，已重试3次]'
                time.sleep(1)
                continue
            except Exception as e:
                # 未预期的异常：立即返回，不重试
                logger.error(f'Unexpected LLM error: {e}', exc_info=True)
                return f'[LLM Error: 发生未预期的错误 - {str(e)[:100]}]'

        if p:
            print(ret)
        return ret


    def chat_stream(self, message: List[dict]):
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
