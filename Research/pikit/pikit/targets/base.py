"""The :class:`Target` abstraction shared by every model backend."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .types import ChatResponse, Message


class Target(ABC):
    """A model backend that turns a prompt into a text completion.

    Subclasses implement :meth:`query`. Backends keep their SDK imports
    local (lazy) so that installing the core package pulls in nothing.

    Tool-calling support via :meth:`chat` is an *optional* capability:
    backends that do not implement it raise ``NotImplementedError``, and
    text-only callers (the direct-injection pipeline, ``ChatAgent``) never
    need it.
    """

    #: Stable identifier for logs (e.g. ``"openai:gpt-4o"``).
    name: str = "target"

    @abstractmethod
    def query(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Send ``prompt`` to the backend and return the text response.

        Parameters
        ----------
        prompt:
            The user prompt (typically already attacked and/or defended).
        system:
            Optional system prompt. Backends without a native system role
            should prepend it to the user prompt.
        **kwargs:
            Backend-specific generation options (e.g. ``temperature``,
            ``max_tokens``).
        """
        raise NotImplementedError

    def chat(
        self,
        messages: List[Message],
        tools: Optional[List[dict]] = None,
        system: Optional[str] = None,
        **kwargs,
    ) -> ChatResponse:
        """Multi-turn, tool-aware completion. **Optional** capability.

        Parameters
        ----------
        messages:
            The conversation so far as normalized :class:`Message` objects.
        tools:
            Provider-agnostic tool schemas, each a dict shaped like
            ``{"name", "description", "parameters": <JSON schema>}``. Each
            backend translates these into its own wire format.
        system:
            Optional system prompt.

        Returns
        -------
        ChatResponse
            Normalized assistant turn (text + any tool calls).
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement tool-calling chat()"
        )

    def __call__(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        return self.query(prompt, system=system, **kwargs)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"{type(self).__name__}(name={self.name!r})"
