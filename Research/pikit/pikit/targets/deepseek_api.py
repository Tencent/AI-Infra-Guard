"""DeepSeek official API backend.

Calls DeepSeek's public API (https://api.deepseek.com) directly using the
``openai`` SDK, with reasoning/thinking mode enabled by default.

This replaces the CodeBuddy proxy endpoint for more stable connectivity
and direct API access.

Install with::

    pip install openai
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, List, Optional

from .base import Target

DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_API_KEY = "sk-29e340964b574612a01032bdea08584e"


class DeepSeekAPITarget(Target):
    """DeepSeek official API target with thinking/reasoning support.

    Parameters
    ----------
    model:
        Model name (default ``deepseek-v4-flash``).
    base_url:
        API endpoint (default ``https://api.deepseek.com``).
    api_key:
        API key. Falls back to ``$DEEPSEEK_API_KEY`` then the built-in default.
    reasoning_effort:
        Reasoning effort level (``"high"``, ``"medium"``, ``"low"``).
        Default ``"high"``.
    thinking_enabled:
        Whether to enable thinking mode via ``extra_body``. Default ``True``.
    max_retries:
        Max retries on transient errors (default 3).
    retry_base_wait:
        Base wait time for exponential backoff in seconds (default 5).
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        reasoning_effort: str = "high",
        thinking_enabled: bool = True,
        max_retries: int = 3,
        retry_base_wait: float = 5.0,
        **client_kwargs,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "the 'openai' package is required for deepseek_api targets; "
                "install with: pip install openai"
            ) from exc

        self.model = model or DEFAULT_MODEL
        self.name = f"deepseek_api:{self.model}"
        self._reasoning_effort = reasoning_effort
        self._thinking_enabled = thinking_enabled
        self._max_retries = max_retries
        self._retry_base_wait = retry_base_wait

        # Build extra_body for thinking mode.
        self._extra_body = {}
        if thinking_enabled:
            self._extra_body["thinking"] = {"type": "enabled"}

        self._client = OpenAI(
            base_url=base_url or DEFAULT_BASE_URL,
            api_key=api_key or os.environ.get("DEEPSEEK_API_KEY") or DEFAULT_API_KEY,
            **client_kwargs,
        )

    def _create_with_retry(self, **params) -> Any:
        """Call chat.completions.create with exponential backoff retries."""
        last_exc = None
        for attempt in range(self._max_retries + 1):
            try:
                return self._client.chat.completions.create(**params)
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    wait = self._retry_base_wait * (2 ** attempt)
                    time.sleep(wait)
                    continue
                raise
        raise last_exc  # type: ignore[misc]

    def _build_params(self, messages, tools=None, **extra) -> dict:
        """Build the create() parameters with reasoning/thinking defaults."""
        params = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        # Add reasoning_effort as a named parameter (supported by DeepSeek API).
        params["reasoning_effort"] = self._reasoning_effort
        # Add thinking mode via extra_body.
        if self._extra_body:
            params["extra_body"] = dict(self._extra_body)
        # Add tools if provided.
        if tools:
            params["tools"] = [{"type": "function", "function": t} for t in tools]
            params["tool_choice"] = "auto"
        # Merge any extra kwargs (e.g. temperature).
        params.update(extra)
        return params

    def query(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        params = self._build_params(messages, **kwargs)
        resp = self._create_with_retry(**params)
        return resp.choices[0].message.content or ""

    def chat(self, messages, tools=None, system=None, **kwargs):
        from .types import ChatResponse, ToolCall

        wire = []
        if system:
            wire.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                wire.append({
                    "role": "assistant",
                    "content": m.content or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.args),
                            },
                        }
                        for tc in m.tool_calls
                    ],
                })
            elif m.role == "tool":
                for tr in m.tool_results:
                    wire.append({
                        "role": "tool",
                        "tool_call_id": tr.id,
                        "content": tr.content,
                    })
            else:
                wire.append({"role": m.role, "content": m.content})

        params = self._build_params(wire, tools=tools, **kwargs)
        resp = self._create_with_retry(**params)

        choice = resp.choices[0]
        msg = choice.message
        calls = []
        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except (json.JSONDecodeError, TypeError):
                args = {}
            calls.append(ToolCall(id=tc.id, name=tc.function.name, args=args))

        return ChatResponse(
            text=msg.content or "",
            tool_calls=calls,
            stop_reason=choice.finish_reason,
            raw=resp,
        )
