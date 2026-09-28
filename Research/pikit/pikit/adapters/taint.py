"""Conditional routing of tainted artifacts into external framework tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional


ToolMatcher = Callable[[Dict[str, Any]], bool]


@dataclass
class ToolTaintRule:
    """A conditional taint response for one tool.

    Parameters
    ----------
    tool_name:
        Name of the framework tool to intercept.
    payload:
        Artifact returned instead of the real tool result on a match.
    when:
        Optional predicate receiving parsed tool arguments.  When omitted,
        every call to ``tool_name`` is tainted.
    """

    tool_name: str
    payload: str
    when: Optional[ToolMatcher] = None

    def matches(self, tool_name: str, args: Dict[str, Any]) -> bool:
        return self.tool_name == tool_name and (
            self.when is None or bool(self.when(args))
        )


class TaintRouter:
    """Resolve tool calls to either clean execution or a tainted artifact."""

    def __init__(
        self,
        rules: Optional[Iterable[ToolTaintRule]] = None,
        *,
        taint: Optional[Dict[str, str]] = None,
    ) -> None:
        self.rules = list(rules or [])
        self.rules.extend(
            ToolTaintRule(tool_name=name, payload=payload)
            for name, payload in (taint or {}).items()
        )

    def resolve(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """Return a tainted artifact when a rule matches, else ``None``."""
        for rule in self.rules:
            if rule.matches(tool_name, args):
                return rule.payload
        return None


__all__ = ["ToolMatcher", "ToolTaintRule", "TaintRouter"]
