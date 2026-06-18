"""OpenAI-compatible LLM client for model-attack.

Minimal wrapper that supports:
- Single-turn chat
- Multi-turn chat with history
- Robust error handling (timeouts, 401, rate limits)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

try:
    from openai import OpenAI, APIError, APIConnectionError, AuthenticationError, RateLimitError
except ImportError:
    OpenAI = None  # type: ignore


@dataclass
class LLMResponse:
    text: str = ""
    model: str = ""
    error: Optional[str] = None
    usage: dict = field(default_factory=dict)
    raw: Optional[dict] = None

    def ok(self) -> bool:
        return self.error is None


class LLMClient:
    def __init__(
        self,
        model: str,
        token: str,
        base_url: str,
        timeout: float = 60.0,
    ):
        if OpenAI is None:
            raise RuntimeError("openai package not installed; run pip install -r requirements.txt")
        self.model = model
        self.client = OpenAI(api_key=token, base_url=base_url, timeout=timeout)

    @classmethod
    def from_env(cls) -> "LLMClient":
        return cls(
            model=os.environ["AIG_TARGET_MODEL"],
            token=os.environ["AIG_TARGET_TOKEN"],
            base_url=os.environ["AIG_TARGET_BASE_URL"],
        )

    def chat(
        self,
        user: str,
        system: str = "",
        temperature: float = 0.9,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        return self._call(messages, temperature, max_tokens)

    def chat_with_history(
        self,
        messages: List[dict],
        temperature: float = 0.9,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        return self._call(messages, temperature, max_tokens)

    def _call(self, messages: list, temperature: float, max_tokens: int) -> LLMResponse:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = resp.choices[0].message.content if resp.choices else ""
            usage = resp.usage.model_dump() if resp.usage else {}
            return LLMResponse(text=text or "", model=self.model, usage=usage)
        except AuthenticationError as e:
            return LLMResponse(error=f"auth_error: {e}")
        except RateLimitError as e:
            return LLMResponse(error=f"rate_limit: {e}")
        except APIConnectionError as e:
            return LLMResponse(error=f"connection_error: {e}")
        except APIError as e:
            return LLMResponse(error=f"api_error: {e}")
        except Exception as e:
            return LLMResponse(error=f"{type(e).__name__}: {e}")

    def list_models(self) -> List[str]:
        try:
            resp = self.client.models.list()
            return [m.id for m in resp.data]
        except Exception:
            return []
