# aig-skill-scan

**[English](./USAGE.md)** | 中文

审计本地 Agent Skill 目录。需要模型 API key，以及要扫描的目录。

```bash
pip install aig-skill-scan
```

需要 Python ≥ 3.9。

## 示例

```bash
export LLM_API_KEY="your-api-key"

aig-skill-scan --repo /path/to/skill -o result.sarif.json

aig-skill-scan --repo /path/to/skill \
  -m deepseek-v4-flash \
  -u https://openrouter.ai/api/v1 \
  --language zh \
  -o result.sarif.json
```

密钥按顺序读取：`-k` / `--api_key`，然后是 `LLM_API_KEY`，再然后是 `OPENAI_API_KEY`。模型名还可以来自 `LLM_MODEL` 或 `OPENAI_MODEL`，接口地址来自 `LLM_BASE_URL` 或 `OPENAI_BASE_URL`。

## 参数

| 参数 | 默认 | 含义 |
| --- | --- | --- |
| `--repo` | — | 要扫描的 Skill 目录。必填。 |
| `-m, --model` | `deepseek-v4-flash` | 模型名。 |
| `-k, --api_key` | 环境变量 | API key。 |
| `-u, --base_url` | `https://openrouter.ai/api/v1` | API 地址。 |
| `-p, --prompt` | — | 这次扫描的附加说明。 |
| `--language` | `zh` | `zh` 或 `en`。 |
| `--debug` | 关闭 | 调试日志。 |
| `-o, --output` | 标准输出 | 结果写到哪里。 |
| `--aig-mode` | 关闭 | 平台模式。自己在命令行运行时不要打开。 |

## 输出

普通运行写出 [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/) JSON。写了 `-o` 就进文件，没写就打印到终端。

`--aig-mode` 只给 AI-Infra-Guard 服务用。它会往标准输出打步骤日志，并把 `-o` 的文件改成内部 JSON。自己运行时不要加。
