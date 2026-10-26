# aig-model-scan

**[English](./USAGE.md)** | 中文

对兼容 OpenAI 接口的模型做越狱和安全评测。

```bash
pip install aig-model-scan
```

需要 Python ≥ 3.12。从源码运行时，`python cli_run.py` 的参数相同。

## 示例

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

`--model`、`--base_url`、`--api_key`、`--max_concurrent` 描述被测模型。要测多个模型，就把这四项按同样的次数重复写上，四组的数量必须一致。

`--simulator_model` 负责生成攻击，`--evaluate_model` 负责给回复打分。某一项不写时，就用被测模型承担那个角色。对应的密钥是 `--sim_api_key` 和 `--eval_api_key`。

API key 只放在你执行的命令里，不要写进仓库。

## 先看有哪些可选项

```bash
aig-model-scan --scan-tools scenarios
aig-model-scan --scan-tools techniques
aig-model-scan --scan-tools metrics
aig-model-scan --show-tool-params PromptInjection
aig-model-scan --list-plugins
```

内置场景名包括 `Bias`、`Toxicity`、`Misinformation`、`IllegalActivity`、`PromptLeakage`、`PIILeakage`、`UnauthorizedAccess`、`ExcessiveAgency`、`Robustness`、`IntellectualProperty`、`Competition`、`GraphicContent`、`PersonalSafety`。

单条提示：

```bash
aig-model-scan \
  --model "gpt-4o-mini" \
  --base_url "https://api.openai.com/v1" \
  --api_key "your-api-key" \
  --max_concurrent 1 \
  --scenarios "Custom:prompt=你好" \
  --techniques Raw
```

一批提示放在文件里：

```bash
aig-model-scan \
  --model "gpt-4o-mini" \
  --base_url "https://api.openai.com/v1" \
  --api_key "your-api-key" \
  --max_concurrent 4 \
  --scenarios "MultiDataset:dataset_file=/path/to/prompts.csv,num_prompts=10,prompt_column=prompt" \
  --techniques Raw
```

## 参数

| 参数 | 默认 | 含义 |
| --- | --- | --- |
| `--model` | — | 被测模型。重复写可增加模型。 |
| `--base_url` | — | 它的 API 地址。每个模型写一次。 |
| `--api_key` | — | 它的 API key。每个模型写一次。 |
| `--max_concurrent` | — | 该模型的并发数。每个模型写一次。 |
| `--scenarios` | — | 一个或多个场景名。 |
| `--techniques` | — | 一个或多个攻击算子名。 |
| `--choice` | `random` | `random`、`serial` 或 `parallel`。 |
| `--async_mode` | 关闭 | 异步执行。 |
| `--metric` | — | 评分指标类名，例如 `RandomMetric`。 |
| `--simulator_model` | 被测模型 | 生成攻击的模型。 |
| `--sim_base_url` | — | 生成模型的 API 地址。 |
| `--sim_api_key` | — | 生成模型的 API key。 |
| `--sim_max_concurrent` | `10` | 生成模型的并发数。 |
| `--evaluate_model` | 被测模型 | 给回复打分的模型。 |
| `--eval_base_url` | — | 评分模型的 API 地址。 |
| `--eval_api_key` | — | 评分模型的 API key。 |
| `--eval_max_concurrent` | `10` | 评分模型的并发数。 |
| `--report` | `logs/report.md` | Markdown 报告路径。 |
| `--progress-log` | `logs/red_team_progress.jsonl` | 已经跑完的用例。传空字符串可关闭。 |
| `--resume` | 关闭 | 跳过进度文件里已经完成的用例。 |
| `--lang` | `zh_CN` | 报告语言。 |
| `--plugins` | — | 额外的插件文件或目录。 |
| `--list-plugins` | — | 打印插件后退出。 |
| `--show-template` | — | `attack`、`metric` 或 `vulnerability`。 |
| `--validate-plugin` | — | 检查一个插件文件或目录。 |
| `--auto-discover` | 关闭 | 从默认目录加载插件。 |
| `--scan-tools` | — | `all`、`techniques`、`metrics` 或 `scenarios`。 |
| `--show-tool-params` | — | 打印某一个算子、指标或场景的参数。 |

## 输出

运行结果写入 `--report` 指向的 Markdown 文件。已经完成的用例会在运行过程中追加到 `--progress-log`。`--resume` 从这份文件接着跑。
