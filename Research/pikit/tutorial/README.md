# 📚 pikit Tutorials — Interactive Jupyter Notebooks

Hands-on, step-by-step guides to using pikit for prompt-injection research.

> **No API key required** — all notebooks use the offline `mock` target.
> Swap `mock` for `openai:`, `anthropic:`, or `hf:` to test against real models.

## Notebooks

| # | Notebook | What you'll learn |
|---|----------|-------------------|
| 1 | [Getting Started](01_getting_started.ipynb) | Core concepts, `craft()` basics, mock target |
| 2 | [Attacks](02_attacks.ipynb) | All 13 attack methods, side-by-side comparison |
| 3 | [Indirect Injection Channels](03_channels_indirect.ipynb) | 16 channels for hiding payloads in carriers |
| 4 | [Defenses](04_defenses.ipynb) | 9 prevention + 3 detection defenses, DefenseHooks |
| 5 | [Agent Testbed](05_agent_testbed.ipynb) | Build agents, taint/sink, run attacks, read traces |
| 6 | [Judges & Batch Experiments](06_judges_and_matrix.ipynb) | RuleJudge, LLMJudge, MatrixRunner, datasets |
| 7 | [Datasets](07_datasets.ipynb) | Built-in benchmarks, custom TOML datasets, result analysis |

## Quick Start

```bash
# Install pikit
pip install -e .

# Launch Jupyter
jupyter notebook tutorial/
```

Open `01_getting_started.ipynb` and follow along.

## Learning Path

```
01 Getting Started → 02 Attacks → 03 Channels
                                          ↓
06 Judges & Matrix ← 05 Agent Testbed ← 04 Defenses
          ↓
07 Datasets
```

- **Beginners**: Go in order (1 → 7).
- **Researchers**: Skip to 5 (Agent Testbed) and 6 (Judges & Matrix).
- **Defenders**: Focus on 4 (Defenses) and 5 (Agent Testbed).

## Using a Real Model

All notebooks default to `mock` (offline). To test real injection outcomes:

```python
from pikit import get_target

# OpenAI / DashScope / vLLM / Ollama
target = get_target("openai:gpt-4o-mini")

# Anthropic Claude
target = get_target("anthropic:claude-sonnet-4-20250514")

# Local HuggingFace
target = get_target("hf:meta-llama/Llama-3-8B-Instruct")
```

Set up your API key first (see the [main README](../README.md) → Configuring model access).
