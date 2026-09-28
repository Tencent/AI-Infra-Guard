# 📚 Jupyter Notebook Tutorials

pikit ships **7 interactive Jupyter notebooks** that walk you through every feature step by step.

> **No API key required** — all notebooks use the offline `mock` target.
> Swap `mock` for `openai:`, `anthropic:`, or `hf:` to test against real models.

## Notebook Index

| # | Notebook | What you'll learn |
|---|----------|-------------------|
| 1 | [Getting Started](https://github.com/NY1024/pikit/blob/main/tutorial/01_getting_started.ipynb) | Core concepts, `craft()` basics, mock target |
| 2 | [Attacks](https://github.com/NY1024/pikit/blob/main/tutorial/02_attacks.ipynb) | All 13 attack methods, side-by-side comparison |
| 3 | [Indirect Injection Channels](https://github.com/NY1024/pikit/blob/main/tutorial/03_channels_indirect.ipynb) | 16 channels for hiding payloads in carriers |
| 4 | [Defenses](https://github.com/NY1024/pikit/blob/main/tutorial/04_defenses.ipynb) | 9 prevention + 3 detection defenses, DefenseHooks |
| 5 | [Agent Testbed](https://github.com/NY1024/pikit/blob/main/tutorial/05_agent_testbed.ipynb) | Build agents, taint/sink, run attacks, read traces |
| 6 | [Judges & Batch Experiments](https://github.com/NY1024/pikit/blob/main/tutorial/06_judges_and_matrix.ipynb) | RuleJudge, LLMJudge, MatrixRunner, datasets |
| 7 | [Datasets](https://github.com/NY1024/pikit/blob/main/tutorial/07_datasets.ipynb) | Built-in benchmarks, custom TOML datasets, result analysis |

## Quick Start

```bash
git clone https://github.com/NY1024/pikit.git
cd pikit
pip install -e .
jupyter notebook tutorial/
```

Open `01_getting_started.ipynb` and follow along — each notebook is self-contained.

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

Set up your API key first (see [Installation](../installation.md) and the [README](https://github.com/NY1024/pikit#configuring-model-access)).
