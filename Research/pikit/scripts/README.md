# Experiment Scripts

This directory contains the experiment runner scripts used to reproduce the
results reported in the paper. All scripts read target and agent configuration
from **environment variables** so they contain no hardcoded endpoints or
credentials.

## Quick Start

```bash
# Install pikit
pip install -e .

# Set your target (any pikit target spec works)
export PIKIT_TARGET="openai:gpt-4o-mini"
# Or use a custom OpenAI-compatible endpoint:
# export PIKIT_TARGET="openai:my-model"
# export OPENAI_BASE_URL="https://api.example.com/v1"
# export OPENAI_API_KEY="sk-..."

# Optional: override agent and concurrency
export PIKIT_AGENT="general_permissive"   # default for most scripts
export PIKIT_WORKERS="5"                   # default concurrency
```

## Scripts

### Full-Scale Experiments (1120 cases)

| Script | Attack | Agent | Judge | Description |
|--------|--------|-------|-------|-------------|
| `run_naive_full_test.py` | `naive` | `general_permissive` | `rule` (3-level) | Baseline: raw payload, no wrapping |
| `run_attacks_full_test.py` | all except `naive` | `general_permissive` | `rule` (3-level) | All attack methods, 5 concurrent threads |

```bash
# Run naive baseline (1120 cases)
python scripts/run_naive_full_test.py

# Run all attacks (12 attacks x 1120 cases = 13,440 runs)
python scripts/run_attacks_full_test.py

# Run a single attack
python scripts/run_attacks_full_test.py --only combined
```

**Output:** `result/naive_full_test/` and `result/attacks/{attack_name}/`

Each attack directory contains:
- `all_results.jsonl` — full traces and verdicts (one JSON per line)
- `all_results.csv` — flat CSV summary
- `summary.json` — aggregate success rates (full / partial / none), per-channel breakdown

### Sampled Experiments (50 cases)

| Script | Attacks | Agent | Judge | Description |
|--------|---------|-------|-------|-------------|
| `run_deepseek_api_eval.py` | 8 attacks | `general` | `llm` | OpenAI-compatible API, full tool pool |
| `run_general_attack_eval.py` | 8 attacks | `general` | `llm` | Neutral system prompt, full tool pool |
| `run_multi_attack_eval.py` | 8 attacks | dataset default | `llm` | Multi-attack comparison |
| `run_improved_judge_test.py` | 13 attacks | `general_permissive` | `rule` (3-level) | Three-level judge validation |

```bash
# Smoke test (3 cases x 8 attacks)
python scripts/run_deepseek_api_eval.py --limit 3 -v

# Full sampled run (50 cases x 8 attacks = 400 runs)
python scripts/run_deepseek_api_eval.py

# Specific attacks only
python scripts/run_general_attack_eval.py --attacks important_instructions combined

# Adjust sample size
python scripts/run_multi_attack_eval.py --sample-size 30
```

### Diagnostic Experiments

| Script | Description |
|--------|-------------|
| `run_deepseek_eval.py` | Naive-only full run (1120 cases) with crash recovery |
| `run_hypothesis_test.py` | Tests 3 hypotheses: permissive prompt, camouflaged payloads, lenient judge |

```bash
# Naive full run with resume capability
python scripts/run_deepseek_eval.py --resume

# Hypothesis testing (small sample, 3 hypotheses x 2 attacks)
python scripts/run_hypothesis_test.py
```

## Output Format

All scripts save results to `result/` subdirectories:

```
result/
  naive_full_test/
    all_results.jsonl      # one result per line, includes full trace
    all_results.csv        # flat CSV for spreadsheet analysis
    summary.json           # aggregate stats: full/partial/none rates
  attacks/
    combined/
      all_results.jsonl
      all_results.csv
      summary.json
    context_ignoring/
      ...
    comparison.json        # cross-attack comparison
  deepseek_api_attack/
    per_attack/
      important_instructions_results.jsonl
      ...
    all_results.jsonl
    comparison_summary.json
    comparison_summary.txt
    run_meta.json
```

### Result Fields (JSONL)

Each line in `all_results.jsonl` contains:

| Field | Type | Description |
|-------|------|-------------|
| `case_id` | string | Dataset case identifier (e.g., `fcm-0042`) |
| `attack` | string | Attack method name |
| `defense` | string | Defense method (usually `none`) |
| `channel` | string | Delivery channel (e.g., `webpage`, `email`, `document`) |
| `agent` | string | Agent scenario key |
| `target` | string | Target model spec |
| `task` | string | Attacker's injected instruction |
| `success` | bool | Full success (canary matched or sink fired with correct args) |
| `partial_success` | bool | Partial success (sink fired with wrong args, canary in context) |
| `success_level` | string | `full` / `partial` / `none` |
| `confidence` | string | Judge confidence level |
| `reason` | string | Judge's reasoning |
| `sink_fired` | bool | Whether a sink tool was called |
| `final_text` | string | Agent's final output |
| `outcome` | string | Outcome enum value |
| `signals` | list | Detection signals |
| `trace` | object | Full agent trace (steps, tool calls, decisions) |

## Environment Variables

| Variable | Default | Used by | Description |
|----------|---------|---------|-------------|
| `PIKIT_TARGET` | `mock` | all scripts | Target spec (e.g., `openai:gpt-4o-mini`, `mock`) |
| `PIKIT_AGENT` | varies | most scripts | Agent scenario key |
| `PIKIT_WORKERS` | `5` | full-scale scripts | Thread pool size |
| `OPENAI_API_KEY` | — | OpenAI targets | API key |
| `OPENAI_BASE_URL` | — | OpenAI targets | Custom endpoint URL |

## Reproducing Paper Results

To reproduce the exact experiment configuration:

```bash
# 1. Naive baseline (1120 cases)
PIKIT_TARGET="your-target" python scripts/run_naive_full_test.py

# 2. All attack methods (12 attacks x 1120 cases)
PIKIT_TARGET="your-target" python scripts/run_attacks_full_test.py

# 3. Cross-attack comparison is automatically saved to:
#    result/attacks/comparison.json
```

The `comparison.json` file contains a side-by-side table of all attacks
with full success rate, partial success rate, any-influence rate, and
sink-fired count.
