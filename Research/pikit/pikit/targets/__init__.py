"""Model backends behind a uniform :class:`Target` interface.

Attack and defense code never imports a backend SDK directly — it calls
:func:`get_target` and uses :meth:`Target.query`. Every backend SDK is
imported lazily inside its own module, so the core package and the mock
target work with zero third-party dependencies installed.
"""

from __future__ import annotations

from .base import Target
from .types import ChatResponse, Message, ToolCall, ToolResult

__all__ = [
    "Target",
    "get_target",
    "ChatResponse",
    "Message",
    "ToolCall",
    "ToolResult",
]


def get_target(spec: str, **kwargs) -> Target:
    """Construct a :class:`Target` from a ``"backend:model"`` spec.

    Parameters
    ----------
    spec:
        One of:

        * ``"openai:<model>"`` — OpenAI or any OpenAI-compatible endpoint
          (vLLM, Ollama, …); pass ``base_url=`` / ``api_key=`` via kwargs.
        * ``"anthropic:<model>"`` — Anthropic Claude.
        * ``"hf:<model>"`` — a local HuggingFace ``transformers`` model.
        * ``"mock"`` — an offline echo target for the **test suite only**
          (echoes input, never executes an injection; not for demos).
    **kwargs:
        Forwarded to the backend constructor.

    Examples
    --------
    >>> get_target("mock")
    MockTarget(...)
    """
    backend, _, model = spec.partition(":")
    backend = backend.strip().lower()

    if backend == "mock":
        from .mock import MockTarget

        return MockTarget(**kwargs)

    if backend in ("openai", "openai_compatible", "vllm", "ollama"):
        from .openai_compatible import OpenAICompatibleTarget

        return OpenAICompatibleTarget(model=model or None, **kwargs)

    if backend == "anthropic":
        from .anthropic import AnthropicTarget

        return AnthropicTarget(model=model or None, **kwargs)

    if backend in ("hf", "huggingface"):
        from .huggingface import HuggingFaceTarget

        if not model:
            raise ValueError("hf target requires a model id, e.g. 'hf:gpt2'")
        return HuggingFaceTarget(model=model, **kwargs)

    if backend in ("codebuddy", "deepseek"):
        from .codebuddy import CodeBuddyTarget

        return CodeBuddyTarget(model=model or None, **kwargs)

    if backend == "deepseek_api":
        from .deepseek_api import DeepSeekAPITarget

        return DeepSeekAPITarget(model=model or None, **kwargs)

    raise ValueError(
        f"unknown target backend {backend!r} in spec {spec!r}; "
        "expected one of: mock, openai, anthropic, hf"
    )
