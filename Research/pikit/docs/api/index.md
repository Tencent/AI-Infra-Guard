# API Reference

Auto-generated reference for pikit's public API, powered by mkdocstrings.

| Module | What it covers |
|---|---|
| [Base Classes](base.md) | `Attack`, `Defense`, `Channel` abstract base classes |
| [Attacks](attacks.md) | `pikit.attacks` — registry and all attack classes |
| [Defenses](defenses.md) | `pikit.defenses` — registry and all defense classes |
| [Channels](channels.md) | `pikit.channels` — registry and all channel classes |
| [Targets](targets.md) | `pikit.targets` — `Target`, `get_target`, data structures |
| [Agent](agent.md) | `pikit.agent` — `Agent`, `Trace`, `DefenseHooks`, `Tool` |
| [craft()](craft.md) | `pikit.craft` — `craft()`, `CraftResult` |
| [Judges](judge.md) | `pikit.judges` — `Judge`, `RuleJudge`, `LLMJudge` |
| [Matrix Runner](matrix.md) | `pikit.matrix` — `MatrixRunner`, `ExperimentConfig`, `ExperimentResult` |
| [Datasets](datasets.md) | `pikit.datasets` — `list_datasets`, `load_dataset`, `run_dataset` |
| [Registry](registry.md) | `pikit.registry` — `Registry` class |

## Quick lookup

```python
# Top-level imports
from pikit import (
    attacks, channels, defenses,    # registries
    Attack, Channel, Defense,       # base classes
    Target, get_target,             # model backends
    craft, CraftResult,             # unified entry point
)

# Agent subsystem
from pikit.agent import (
    get_agent, DefenseHooks,        # agent factory + defense hooks
    Agent, Trace, TraceStep,        # base class + trace types
    Tool, tool,                     # tool wrapper + decorator
)
```
