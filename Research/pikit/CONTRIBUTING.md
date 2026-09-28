# Contributing to pikit

Thank you for your interest in improving pikit! This guide covers the basics.

## Adding a new attack / defense / channel / detector

pikit uses a decorator-based registry. Adding a new method is a **single file** — no edits to core code needed.

### 1. Create the file

Place it in the appropriate subdirectory:

| Type | Directory | Base class |
|------|-----------|------------|
| Attack | `pikit/attacks/` | `pikit.base.Attack` |
| Defense (prevention) | `pikit/defenses/` | `pikit.base.Defense` |
| Defense (detection) | `pikit/defenses/detection.py` | `pikit.defenses.detection.DetectionDefense` |
| Channel | `pikit/channels/` | `pikit.base.Channel` |

### 2. Implement the method

```python
from ..base import Attack
from . import register

@register("my_attack")
class MyAttack(Attack):
    """One-line description of what this attack does."""

    def inject(self, prompt: str, injected_task: str) -> str:
        # Transform the prompt to smuggle in injected_task.
        return prompt + "\n" + injected_task
```

### 3. Register the import

Add your module to the `__init__.py` import list in the same directory. For attacks:

```python
from . import (  # noqa: E402,F401
    naive,
    ...
    my_attack,   # <-- add here
)
```

### 4. Write a test

Add a test in `tests/test_attacks.py` (or the appropriate test file):

```python
def test_my_attack_registered():
    from pikit import attacks
    assert "my_attack" in attacks.list()

def test_my_attack_injects():
    from pikit import attacks
    atk = attacks.get("my_attack")()
    result = atk.inject("benign", "evil task")
    assert "evil task" in result
```

### 5. Run tests

```bash
pytest -v
```

## Adding a new agent scenario

1. Create a file in `pikit/agent/scenarios/`.
2. Subclass `ToolAgent` (or `Agent`), configure tools and system prompt.
3. Use `@register("my_scenario")` to register it.
4. Add the import to `scenarios/__init__.py`.
5. Define which tool is the **taint point** and which is the **sink**.

## Adding a new target backend

1. Create a file in `pikit/targets/`.
2. Subclass `Target`, implement `query()` and optionally `chat()`.
3. Add the backend to `get_target()` in `targets/__init__.py`.
4. Keep SDK imports **lazy** (inside `__init__` or methods) so core stays zero-dependency.
5. Add the dependency to `pyproject.toml` under `[project.optional-dependencies]`.

## Code style

- Python 3.9+ compatible (use `from __future__ import annotations`).
- Zero runtime dependencies for core (lazy imports for backends).
- Every public class and function has a docstring.
- Doctests in docstrings for self-documenting examples.
- Type hints on all signatures.

## Running the test suite

```bash
pip install -e ".[dev]"
pytest -v
```

All tests are offline (use `MockTarget`) — no API key needed.

## Submitting changes

1. Fork the repo and create a feature branch.
2. Write tests for your changes.
3. Ensure `pytest -v` passes.
4. Open a pull request with a clear description.

## Reporting issues

Use [GitHub Issues](https://github.com/NY1024/pikit/issues) to report bugs or suggest features.