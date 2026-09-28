"""Stable, registry-backed harness protocol used by matrix experiments."""
from __future__ import annotations
from typing import Any, Callable, Dict, Protocol, Type
from ..agent.base import Trace

class AgentHarness(Protocol):
    """An executable agent environment that returns a pikit trace."""
    name: str
    def run(self, user_message: str, **kwargs: Any) -> Trace: ...

_HARNESS_REGISTRY: Dict[str, Type[Any]] = {}


def register_harness(name: str) -> Callable[[Type[Any]], Type[Any]]:
    """Register a harness class for matrix/runtime configuration."""
    def decorator(cls: Type[Any]) -> Type[Any]:
        _HARNESS_REGISTRY[name] = cls
        return cls
    return decorator


def get_harness(name: str) -> Type[Any]:
    """Return a registered harness class."""
    try:
        return _HARNESS_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"unknown harness {name!r}; available: {sorted(_HARNESS_REGISTRY)}") from exc


def list_harnesses() -> list[str]:
    """Return registered harness names."""
    return sorted(_HARNESS_REGISTRY)


__all__ = ["AgentHarness", "register_harness", "get_harness", "list_harnesses"]
