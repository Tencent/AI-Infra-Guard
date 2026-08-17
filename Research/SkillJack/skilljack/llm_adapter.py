"""
LLM Adapter — wraps a custom API endpoint to be compatible with
SkillX's LLM interface (which expects langchain-style ainvoke/invoke).

This lets you use any OpenAI-compatible API with SkillX's full
extraction pipeline without modifying SkillX's source code.

Supports: DeepSeek, OpenAI, vLLM, or any OpenAI-compatible endpoint.
"""
from __future__ import annotations

import asyncio
import json
import re
import logging
import time
from typing import Optional, Callable, Any, List, Tuple, Union

import requests

logger = logging.getLogger(__name__)

MessageType = Tuple[str, str]


class CompatibleLLM:
    """
    LLM client compatible with SkillX's LLM interface.

    Implements:
      - ainvoke(messages, regex_pattern, regex_extractor, **kwargs) -> str
      - invoke(messages, ...) -> str

    Internally uses requests.post to an OpenAI-compatible endpoint.
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        max_tokens: int = 8192,
        temperature: float = 0.7,
        max_retries: int = 5,
        retry_delay: float = 3.0,
        timeout: int = 120,
        **kwargs,
    ):
        # Import config lazily to allow standalone usage
        try:
            from skilljack.config import (
                LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
                LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_TIMEOUT, LLM_MAX_RETRIES,
            )
        except ImportError:
            LLM_API_KEY = "your-api-key"
            LLM_BASE_URL = "https://api.openai.com/v1/chat/completions"
            LLM_MODEL = "gpt-4"
            LLM_MAX_TOKENS = 8192
            LLM_TEMPERATURE = 0.3
            LLM_TIMEOUT = 120
            LLM_MAX_RETRIES = 5

        self.api_key = api_key or LLM_API_KEY
        self.base_url = base_url or LLM_BASE_URL
        self.model = model or LLM_MODEL
        self.max_tokens = max_tokens or LLM_MAX_TOKENS
        self.temperature = temperature if temperature is not None else LLM_TEMPERATURE
        self.max_retries = max_retries or LLM_MAX_RETRIES
        self.retry_delay = retry_delay
        self.timeout = timeout or LLM_TIMEOUT
        self.kwargs = kwargs
        self.call_count = 0
        self.total_tokens = 0

    def _convert_messages(
        self, messages: List[Union[MessageType, dict, Any]]
    ) -> list[dict]:
        """Convert SkillX message format to OpenAI chat format."""
        converted = []
        for msg in messages:
            if isinstance(msg, tuple):
                role, content = msg
                # SkillX uses "human" / "system" / "assistant"
                role_map = {"human": "user", "ai": "assistant"}
                converted.append({
                    "role": role_map.get(role, role),
                    "content": content,
                })
            elif isinstance(msg, dict):
                converted.append(msg)
            elif hasattr(msg, "content") and hasattr(msg, "type"):
                # LangChain message objects
                role_map = {
                    "human": "user",
                    "ai": "assistant",
                    "system": "system",
                }
                converted.append({
                    "role": role_map.get(msg.type, msg.type),
                    "content": msg.content,
                })
            else:
                converted.append({"role": "user", "content": str(msg)})
        return converted

    def _call_api(self, messages: list[dict]) -> str:
        """Make the actual API call."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(
            self.base_url, headers=headers, json=payload, timeout=self.timeout
        )
        if resp.status_code != 200:
            raise Exception(f"API error {resp.status_code}: {resp.text[:300]}")

        result = resp.json()
        self.call_count += 1
        if result.get("usage"):
            self.total_tokens += result["usage"].get("total_tokens", 0)
        return result["choices"][0]["message"]["content"]

    async def ainvoke(
        self,
        messages: List[Union[MessageType, dict, Any]],
        regex_pattern: Optional[str] = None,
        regex_extractor: Optional[Callable[[str], Any]] = None,
        **kwargs,
    ) -> str:
        """Async invoke — compatible with SkillX's interface."""
        await asyncio.sleep(0.2)  # small delay to prevent burst

        converted = self._convert_messages(messages)
        retry_count = 0

        while retry_count < self.max_retries:
            try:
                response_text = await asyncio.get_event_loop().run_in_executor(
                    None, self._call_api, converted
                )

                if regex_extractor:
                    extracted = regex_extractor(response_text)
                    if extracted is None:
                        logger.warning(
                            f"Regex extraction failed, retry "
                            f"({retry_count + 1}/{self.max_retries})"
                        )
                        retry_count += 1
                        await asyncio.sleep(self.retry_delay)
                        continue
                    return response_text

                if regex_pattern:
                    if not re.search(regex_pattern, response_text):
                        logger.warning(
                            f"Regex pattern not found, retry "
                            f"({retry_count + 1}/{self.max_retries})"
                        )
                        retry_count += 1
                        await asyncio.sleep(self.retry_delay)
                        continue

                return response_text

            except Exception as e:
                error_msg = str(e).lower()
                logger.error(f"LLM error ({retry_count + 1}): {str(e)[:100]}")

                if any(kw in error_msg for kw in [
                    "rate limit", "429", "too many requests"
                ]):
                    sleep_time = min(self.retry_delay * (2 ** retry_count), 60)
                    await asyncio.sleep(sleep_time)
                    retry_count += 1
                    continue

                retry_count += 1
                if retry_count >= self.max_retries:
                    raise
                await asyncio.sleep(self.retry_delay)

        raise Exception(f"Failed after {self.max_retries} retries")

    def invoke(
        self,
        messages: List[Union[MessageType, dict, Any]],
        regex_pattern: Optional[str] = None,
        regex_extractor: Optional[Callable[[str], Any]] = None,
        **kwargs,
    ) -> str:
        """Sync invoke wrapper."""
        return asyncio.run(
            self.ainvoke(messages, regex_pattern, regex_extractor, **kwargs)
        )

    def stats(self) -> dict:
        return {
            "total_calls": self.call_count,
            "total_tokens": self.total_tokens,
        }
