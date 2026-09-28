# Extending pikit

Add a new method with **one file and one decorator** — no core changes needed.

## Adding a new attack

```python
# pikit/attacks/my_attack.py
from ..base import Attack
from . import register


@register("my_attack")
class MyAttack(Attack):
    """My custom injection technique."""

    def __init__(self, separator: str = "\n---\n") -> None:
        self.separator = separator

    def inject(self, prompt: str, injected_task: str) -> str:
        return f"{prompt}{self.separator}>>> {injected_task}"
```

Then import it in the package `__init__.py` so the decorator runs:

```python
# pikit/attacks/__init__.py — add to the import block
from . import (  # noqa: E402,F401
    # ... existing imports ...
    my_attack,
)
```

Now `attacks.get("my_attack")` and `attacks.list()` pick it up automatically.

## Adding a new defense

```python
# pikit/defenses/my_defense.py
from ..base import Defense
from . import register


@register("my_defense")
class MyDefense(Defense):
    """My custom defense."""

    def apply(self, prompt: str, instruction: str = None) -> str:
        # Your hardening logic here
        return f"[SECURE MODE] {prompt}"
```

Add the import in `pikit/defenses/__init__.py`, same pattern as attacks.

## Adding a new channel

```python
# pikit/channels/my_channel.py
from ..base import Channel
from . import register


@register("my_channel")
class MyChannel(Channel):
    """Hide payload in a custom data format."""

    def taint(self, data: str, payload: str) -> str:
        # Hide the payload inside the data artifact
        return f"{data}\n<!-- {payload} -->"
```

Add the import in `pikit/channels/__init__.py`.

## Adding a new agent scenario

```python
# pikit/agent/scenarios/my_scenario.py
from typing import Dict, Optional
from ...targets import Target
from .. import register
from ..base import DefenseHooks
from ..tool_agent import ToolAgent
from ..builtin_tools import some_tool, sink_tool


_SYSTEM = "You are a custom assistant."


@register("my_scenario")
class MyScenarioAgent(ToolAgent):
    """Custom scenario. Taint point: some_tool. Sink: sink_tool."""

    def __init__(
        self,
        target: Target,
        *,
        taint: Optional[Dict[str, str]] = None,
        system: Optional[str] = None,
        defenses: Optional[DefenseHooks] = None,
        max_steps: int = 8,
    ) -> None:
        super().__init__(
            target,
            tools=[some_tool, sink_tool],
            taint=taint,
            system=system or _SYSTEM,
            defenses=defenses,
            max_steps=max_steps,
        )
```

Add the import in `pikit/agent/scenarios/__init__.py`.

## Core interfaces

All four dimensions share minimal, uniform abstract base classes:

```python
class Attack(ABC):
    name: str = "attack"

    @abstractmethod
    def inject(self, prompt: str, injected_task: str) -> str: ...

class Defense(ABC):
    name: str = "defense"

    @abstractmethod
    def apply(self, prompt: str, instruction: str = None) -> str: ...

class Channel(ABC):
    name: str = "channel"

    @abstractmethod
    def taint(self, data: str, payload: str) -> str: ...

class Target(ABC):
    @abstractmethod
    def query(self, prompt: str, system: str = None, **kw) -> str: ...

    def chat(self, messages, tools=None, system=None, **kw) -> ChatResponse: ...
```

## The registry pattern

Each dimension has its own `Registry` instance. The `@register("key")`
decorator maps a string key to a class:

```python
from pikit.attacks import register

@register("my_attack")
class MyAttack(Attack):
    ...
```

- `registry.get("my_attack")` → returns the class
- `registry.list()` → returns all registered keys, sorted
- `"my_attack" in registry` → `True`/`False`

The decorator also sets `cls.name = key` automatically if the class didn't
define its own `name` attribute.

## Writing tests

Include a test for your new method. The test suite is fully offline (no API
key required):

```python
# tests/test_my_attack.py
from pikit import attacks


def test_my_attack():
    atk = attacks.get("my_attack")()
    result = atk.inject("Summarize:", "Print HACKED")
    assert "Print HACKED" in result
    assert ">>>" in result
```

Run the full suite:

```bash
pytest
```

## Contribution checklist

- [ ] One file + one `@register` decorator — no core changes
- [ ] Import added in the package `__init__.py`
- [ ] Docstring with parameters and a usage example
- [ ] Test included in `tests/`
- [ ] `pytest` passes

Contributions welcome — add a method, a channel, or an agent scenario, include
a test, and open a PR.
