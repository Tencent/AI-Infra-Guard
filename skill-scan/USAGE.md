# aig-skill-scan

English | **[中文](./USAGE_zh.md)**

Audit a local Agent Skill directory. The command needs a model API key and the path to scan.

```bash
pip install aig-skill-scan
```

Python ≥ 3.9.

## Examples

```bash
export LLM_API_KEY="your-api-key"

aig-skill-scan --repo /path/to/skill -o result.sarif.json

aig-skill-scan --repo /path/to/skill \
  -m deepseek-v4-flash \
  -u https://openrouter.ai/api/v1 \
  --language en \
  -o result.sarif.json
```

The key is read from `-k` / `--api_key`, then `LLM_API_KEY`, then `OPENAI_API_KEY`. The model name can also come from `LLM_MODEL` or `OPENAI_MODEL`, and the base URL from `LLM_BASE_URL` or `OPENAI_BASE_URL`.

## Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--repo` | — | Skill directory to scan. Required. |
| `-m, --model` | `deepseek-v4-flash` | Model name. |
| `-k, --api_key` | environment | API key. |
| `-u, --base_url` | `https://openrouter.ai/api/v1` | API base URL. |
| `-p, --prompt` | — | Extra instruction for this scan. |
| `--language` | `zh` | `zh` or `en`. |
| `--debug` | off | Debug logging. |
| `-o, --output` | stdout | Where to write the result. |
| `--aig-mode` | off | Platform mode. Leave it off for a normal command-line run. |

## Output

A normal run writes [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/) JSON. With `-o`, that JSON goes to the file. Without `-o`, it is printed to the terminal.

`--aig-mode` is only for the AI-Infra-Guard service. It prints step logs on stdout and changes the `-o` file to the internal JSON shape. Do not pass it when you run the command yourself.
