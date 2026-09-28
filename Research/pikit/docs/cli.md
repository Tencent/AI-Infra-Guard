# CLI

After `pip install pikit`, the `pikit` command is available everywhere.

## `pikit list`

List all registered methods — agents, attacks, channels, defenses, and
detectors.

```bash
pikit list
```

## `pikit show`

Offline preview of method outputs — **no API key needed**. Great for
understanding what each method does before spending tokens.

```bash
pikit show attacks     # see every attack wording the same task
pikit show defenses    # see each defense hardening a tainted prompt
pikit show channels    # see where each channel hides the payload
```

## `pikit run`

Run a single attack combination against any configured target. `mock` works
offline; OpenAI-compatible endpoints require `OPENAI_API_KEY` and usually
`OPENAI_BASE_URL`.

```bash
pikit run --agent chat --attack context_ignoring --defense spotlighting
pikit run --agent browser --attack combined --channel webpage --defense sandwich
pikit run --target mock --agent chat --attack naive
pikit run --target openai:deepseek-v4-flash --base-url https://api.deepseek.com \
  --agent chat --attack context_ignoring
```

Options:

| Flag | Description |
|------|-------------|
| `--agent` | Agent key (chat/email/rag/browser/coding/tool) |
| `--attack` | Attack key |
| `--channel` | Channel key (or `none` for direct) |
| `--defense` | Defense key (or `none`) |
| `--task` | Attacker's injected instruction |
| `--user-message` | Normal user request |
| `--data-sample` | Sample to taint (webpage/email/document/code/skill) |
| `--target` | Target spec: `mock`, `openai:<model>`, `anthropic:<model>`, or `hf:<model>` |
| `--base-url` | OpenAI-compatible endpoint override |
| `--model` | Deprecated shortcut for an OpenAI-compatible model id |
| `--config` | TOML config file |

`--runtime` currently accepts the CLI-configurable Runtime Harnesses
`openclaw` and `hermes`. LangChain, OpenAI Agents SDK, and PydanticAI require
a configured Python adapter instance and are demonstrated in
`demos/framework_adapters/`.

## `pikit matrix`

Run a batch experiment from a TOML config file. Outputs results to JSON or
CSV, JSONL, or JSON and prints a summary.

```bash
# basic run
pikit matrix --config experiment.toml

# save results
pikit matrix --config experiment.toml --output results.json
pikit matrix --config experiment.toml --output results.csv
pikit matrix --config experiment.toml --output results.jsonl

# override target or judge
pikit matrix --config experiment.toml --target openai:gpt-4o-mini --judge llm

# statistical sampling: multiple runs with temperature
pikit matrix --config experiment.toml --temperature 0.7 --repeats 5 --output results.json
```

| Flag | Description |
|------|-------------|
| `--config` | TOML experiment config file |
| `--output` | Save results to JSON or CSV |
| `--target` | Override target spec |
| `--judge` | Override judge type (rule/llm/none) |
| `--temperature` | Sampling temperature (0.0=deterministic, 0.7-1.0=stochastic) |
| `--repeats` | Run each combination N times (default 1) |

## `pikit dataset`

Run standard benchmark datasets for full-coverage evaluation. No API key
needed with `--target mock`.

```bash
# list available datasets
pikit dataset list

# run a dataset with mock target
pikit dataset run direct_injection --target mock

# run with a real model and save results
pikit dataset run indirect_injection --target openai:gpt-4o-mini --output results.json

# statistical sampling
pikit dataset run direct_injection --target openai:gpt-4o-mini --temperature 0.7 --repeats 5
```

| Flag | Description |
|------|-------------|
| `name` | Dataset name (direct_injection, indirect_injection) |
| `--output` | Save results to JSON or CSV |
| `--target` | Override target spec |
| `--judge` | Override judge type (rule/llm/none) |
| `--temperature` | Sampling temperature |
| `--repeats` | Run each case N times |

See [Datasets](datasets.md) for the full dataset specification and how to
add custom datasets.

## `pikit runtime`

Create and check isolated OpenClaw or Hermes fixture profiles. The command
does not write API keys or enable real side-effecting tools.

```bash
pikit runtime init openclaw ./runtime/openclaw
pikit runtime doctor openclaw ./runtime/openclaw --json

pikit runtime init hermes ./runtime/hermes
pikit runtime doctor hermes ./runtime/hermes
```

## `pikit report`

Render a concise result summary from JSON or JSONL output:

```bash
pikit report results.jsonl
pikit report results.jsonl --format html --output report.html
```

## Experiment config format

See [`demos/experiment.example.toml`](https://github.com/NY1024/pikit/blob/main/demos/experiment.example.toml)
for a complete annotated example.

```toml
[target]
spec = "mock"  # or "openai:gpt-4o-mini"
# base_url = "https://api.deepseek.com"

[matrix]
attacks  = ["naive", "context_ignoring"]
defenses = ["none", "spotlighting"]
channels = [""]
agents   = ["chat"]

[judge]
type = "rule"       # "rule", "llm", or "none"
canary = "HACKED"
require_sink = false
```

## `demos/run.py` (legacy)

The original `demos/run.py` script is still available and supports the same
options. It is better suited for interactive, single-run exploration:

```bash
python demos/run.py --agent coding --attack context_ignoring --channel skills
```

See [Demos & CLI](demos.md) for full `run.py` documentation.
