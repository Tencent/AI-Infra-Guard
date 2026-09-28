"""Anthropic Claude backend.

The ``anthropic`` package is imported lazily so the core install needs
nothing.

Install with::

    pip install pikit[anthropic]
"""

from __future__ import annotations

import os
from typing import Optional

from .base import Target


class AnthropicTarget(Target):
    """Messages-API backend for Anthropic Claude models.

    Parameters
    ----------
    model:
        Model id (e.g. ``"claude-sonnet-4-6"``).
    api_key:
        API key; falls back to ``$ANTHROPIC_API_KEY``.
    max_tokens:
        Default response cap (Anthropic requires it on every call).
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_tokens: int = 1024,
        **client_kwargs,
    ) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise ImportError(
                "the 'anthropic' package is required for anthropic targets; "
                "install with: pip install pikit[anthropic]"
            ) from exc

        self.model = model or "claude-sonnet-4-6"
        self.name = f"anthropic:{self.model}"
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            **client_kwargs,
        )

    def query(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        kwargs.setdefault("max_tokens", self.max_tokens)
        if system:
            kwargs["system"] = system
        resp = self._client.messages.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        # Concatenate text blocks of the response.
        return "".join(
            block.text for block in resp.content if getattr(block, "type", "") == "text"
        )

    def chat(self, messages, tools=None, system=None, **kwargs):
        from .types import ChatResponse, ToolCall

        kwargs.setdefault("max_tokens", self.max_tokens)
        if system:
            kwargs["system"] = system

        wire = []
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                blocks = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.args,
                        }
                    )
                wire.append({"role": "assistant", "content": blocks})
            elif m.role == "tool":
                # Anthropic returns tool results as a *user* message of
                # tool_result content blocks.
                wire.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tr.id,
                                "content": tr.content,
                            }
                            for tr in m.tool_results
                        ],
                    }
                )
            else:
                wire.append({"role": m.role, "content": m.content})

        if tools:
            # Anthropic uses `input_schema` rather than `parameters`.
            kwargs["tools"] = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get("parameters", {"type": "object"}),
                }
                for t in tools
            ]

        resp = self._client.messages.create(
            model=self.model, messages=wire, **kwargs
        )
        text = "".join(
            b.text for b in resp.content if getattr(b, "type", "") == "text"
        )
        calls = [
            ToolCall(id=b.id, name=b.name, args=dict(b.input or {}))
            for b in resp.content
            if getattr(b, "type", "") == "tool_use"
        ]
        return ChatResponse(
            text=text,
            tool_calls=calls,
            stop_reason=resp.stop_reason,
            raw=resp,
        )
