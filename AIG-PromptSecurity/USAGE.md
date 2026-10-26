# aig-model-scan

English | **[中文](./USAGE_zh.md)**

Run a jailbreak and safety evaluation against an OpenAI-compatible model API.

```bash
pip install aig-model-scan
```

Python ≥ 3.12. From a source checkout, `python cli_run.py` accepts the same flags.

## Examples

```bash
aig-model-scan \
  --model "gpt-4o-mini" \
  --base_url "https://api.openai.com/v1" \
  --api_key "your-api-key" \
  --max_concurrent 10 \
  --scenarios Bias \
  --techniques Raw \
  --report logs/report.md
```

`--model`, `--base_url`, `--api_key`, and `--max_concurrent` describe the model under test. Repeat the four flags together to test more than one model. The four lists must be the same length.

`--simulator_model` generates attacks, and `--evaluate_model` scores replies. Omit either one and that role uses the model under test. Their keys are `--sim_api_key` and `--eval_api_key`.

Pass the API key only on the command you run. Do not commit it.

## List what you can run

```bash
aig-model-scan --scan-tools scenarios
aig-model-scan --scan-tools techniques
aig-model-scan --scan-tools metrics
aig-model-scan --show-tool-params PromptInjection
aig-model-scan --list-plugins
```

Built-in scenario names include `Bias`, `Toxicity`, `Misinformation`, `IllegalActivity`, `PromptLeakage`, `PIILeakage`, `UnauthorizedAccess`, `ExcessiveAgency`, `Robustness`, `IntellectualProperty`, `Competition`, `GraphicContent`, and `PersonalSafety`.

A one-off prompt:

```bash
aig-model-scan \
  --model "gpt-4o-mini" \
  --base_url "https://api.openai.com/v1" \
  --api_key "your-api-key" \
  --max_concurrent 1 \
  --scenarios "Custom:prompt=Say hello" \
  --techniques Raw
```

A file of prompts:

```bash
aig-model-scan \
  --model "gpt-4o-mini" \
  --base_url "https://api.openai.com/v1" \
  --api_key "your-api-key" \
  --max_concurrent 4 \
  --scenarios "MultiDataset:dataset_file=/path/to/prompts.csv,num_prompts=10,prompt_column=prompt" \
  --techniques Raw
```

## Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--model` | — | Model under test. Repeat to add another model. |
| `--base_url` | — | Its API base URL. Repeat once per model. |
| `--api_key` | — | Its API key. Repeat once per model. |
| `--max_concurrent` | — | Concurrent requests for that model. Repeat once per model. |
| `--scenarios` | — | One or more scenario names. |
| `--techniques` | — | One or more attack technique names. |
| `--choice` | `random` | `random`, `serial`, or `parallel`. |
| `--async_mode` | off | Run asynchronously. |
| `--metric` | — | Metric class name, for example `RandomMetric`. |
| `--simulator_model` | model under test | Model that generates attacks. |
| `--sim_base_url` | — | Simulator API base URL. |
| `--sim_api_key` | — | Simulator API key. |
| `--sim_max_concurrent` | `10` | Simulator concurrency. |
| `--evaluate_model` | model under test | Model that scores replies. |
| `--eval_base_url` | — | Evaluator API base URL. |
| `--eval_api_key` | — | Evaluator API key. |
| `--eval_max_concurrent` | `10` | Evaluator concurrency. |
| `--report` | `logs/report.md` | Markdown report path. |
| `--progress-log` | `logs/red_team_progress.jsonl` | Cases finished so far. An empty value disables it. |
| `--resume` | off | Skip cases already recorded in the progress log. |
| `--lang` | `zh_CN` | Report language. |
| `--plugins` | — | Extra plugin file or directory. |
| `--list-plugins` | — | Print plugins and exit. |
| `--show-template` | — | `attack`, `metric`, or `vulnerability`. |
| `--validate-plugin` | — | Check one plugin file or directory. |
| `--auto-discover` | off | Load plugins from the default directories. |
| `--scan-tools` | — | `all`, `techniques`, `metrics`, or `scenarios`. |
| `--show-tool-params` | — | Print the parameters of one technique, metric, or scenario. |

## Output

The run writes a Markdown report to `--report`. Finished cases are appended to `--progress-log` while the run is still going. `--resume` continues from that file.
