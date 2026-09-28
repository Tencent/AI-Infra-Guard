"""Tools for agents: a :class:`Tool` wrapper and a ``@tool`` decorator.

A tool is a plain Python function plus a JSON-schema description the model
uses to decide how to call it. The schema is auto-derived from the
function's type hints (zero dependencies — no pydantic), and can be
overridden explicitly when richer per-argument descriptions are needed.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

# Minimal Python-type -> JSON-schema-type mapping.
_JSON_TYPES = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _derive_parameters(func: Callable) -> dict:
    """Build a JSON-schema ``parameters`` object from a function signature."""
    sig = inspect.signature(func)
    props: Dict[str, dict] = {}
    required = []
    for pname, param in sig.parameters.items():
        if pname == "self" or param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        ann = param.annotation
        jtype = _JSON_TYPES.get(ann, "string")
        props[pname] = {"type": jtype}
        if param.default is inspect.Parameter.empty:
            required.append(pname)
    return {"type": "object", "properties": props, "required": required}


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return str(value)


@dataclass
class Tool:
    """A callable tool exposed to an agent's model.

    Parameters
    ----------
    name, description, func:
        Identity, model-facing description, and the underlying callable.
    parameters:
        JSON-schema for the arguments. Auto-derived if not given.
    is_sink:
        Marks an externally-observable action (e.g. ``send_email``). The
        trace highlights when a sink fires — the key signal for judging
        whether an injection succeeded.
    category:
        Tool category for pool-based selection. One of: ``"web"``,
        ``"email"``, ``"file"``, ``"code"``, ``"knowledge"``,
        ``"communication"``, ``"general"``.
    """

    name: str
    description: str
    func: Callable[..., Any]
    parameters: dict = field(default_factory=lambda: {"type": "object", "properties": {}})
    is_sink: bool = False
    category: str = "general"

    def to_schema(self) -> dict:
        """Return the provider-agnostic ``{name, description, parameters}``."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def __call__(self, **kwargs) -> str:
        return _stringify(self.func(**kwargs))


def tool(
    name: Optional[str] = None,
    *,
    description: Optional[str] = None,
    is_sink: bool = False,
    parameters: Optional[dict] = None,
    category: str = "general",
) -> Callable[[Callable], Tool]:
    """Decorator turning a plain function into a :class:`Tool`.

    The tool ``name`` defaults to the function name; ``description`` to its
    docstring. ``parameters`` is auto-derived from type hints unless given.
    ``category`` tags the tool for pool-based selection by scenario agents.

    Examples
    --------
    >>> @tool(description="Fetch a URL and return its body.", category="web")
    ... def fetch_url(url: str) -> str:
    ...     return "<html>...</html>"
    >>> isinstance(fetch_url, Tool)
    True
    """

    def decorator(func: Callable) -> Tool:
        return Tool(
            name=name or func.__name__,
            description=description or (inspect.getdoc(func) or "").strip(),
            func=func,
            parameters=parameters or _derive_parameters(func),
            is_sink=is_sink,
            category=category,
        )

    return decorator
