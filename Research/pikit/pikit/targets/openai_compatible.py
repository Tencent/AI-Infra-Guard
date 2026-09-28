"""OpenAI / OpenAI-compatible chat backend.

Works with the official OpenAI API and any OpenAI-compatible server
(vLLM, Ollama's ``/v1`` endpoint, LM Studio, …) by pointing ``base_url``
at it. The ``openai`` package is imported lazily so the core install needs
nothing.

Install with::

    pip install pikit[openai]
"""

from __future__ import annotations

import os
from typing import Optional

from .base import Target


class OpenAICompatibleTarget(Target):
    """Chat-completions backend for OpenAI-compatible endpoints.

    Parameters
    ----------
    model:
        Model name (e.g. ``"gpt-4o"`` or a local model id served by vLLM).
    base_url:
        Override the endpoint for a compatible server. Falls back to
        ``$OPENAI_BASE_URL``; defaults to the OpenAI API when unset.
    api_key:
        API key. Falls back to ``$OPENAI_API_KEY``. Some local servers
        accept any value.

    Notes
    -----
    Prefer setting ``OPENAI_API_KEY`` / ``OPENAI_BASE_URL`` in the
    environment over passing secrets as literals — keys passed as string
    arguments are easy to leak into shell history, logs, or version control.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        **client_kwargs,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise ImportError(
                "the 'openai' package is required for openai targets; "
                "install with: pip install pikit[openai]"
            ) from exc

        self.model = model or "gpt-4o-mini"
        self.name = f"openai:{self.model}"
        self._client = OpenAI(
            base_url=base_url or os.environ.get("OPENAI_BASE_URL"),
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            **client_kwargs,
        )

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
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        return resp.choices[0].message.content or ""

    def chat(self, messages, tools=None, system=None, **kwargs):
        import json

        from .types import ChatResponse, ToolCall

        wire = []
        if system:
            wire.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                wire.append(
                    {
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
                    }
                )
            elif m.role == "tool":
                for tr in m.tool_results:
                    wire.append(
                        {
                            "role": "tool",
                            "tool_call_id": tr.id,
                            "content": tr.content,
                        }
                    )
            else:
                wire.append({"role": m.role, "content": m.content})

        params = dict(model=self.model, messages=wire, **kwargs)
        if tools:
            params["tools"] = [
                {"type": "function", "function": t} for t in tools
            ]
            params["tool_choice"] = "auto"

        resp = self._client.chat.completions.create(**params)
        choice = resp.choices[0]
        msg = choice.message
        calls = []
        for tc in msg.tool_calls or []:
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
