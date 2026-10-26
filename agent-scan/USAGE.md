# aig-agent-scan

English | **[中文](./USAGE_zh.md)**

Send test prompts to a running Agent and write a JSON report. The scanner model and the Agent under test are configured separately.

```bash
pip install aig-agent-scan
```

Python ≥ 3.10.

## Examples

```bash
export LLM_API_KEY="your-api-key"

aig-agent-scan --agent_provider target.yaml -o result.json

aig-agent-scan --agent_provider target.yaml \
  --skills data-leakage-detection,tool-abuse-detection \
  --language en \
  -o result.json
```

`target.yaml` describes the Agent being tested, not the scanner model:

```yaml
targets:
  - id: "http"
    config:
      url: "http://127.0.0.1:18081"
      endpoint: "/chat"
      method: "POST"
      headers:
        Content-Type: "application/json"
      body:
        message: "{{prompt}}"
      transform_response: "reply"
```

For a custom HTTP body, `transform_response` is the JSON field that holds the Agent's reply, such as `reply` or `data.text`. Built-in targets such as `openai`, `dify`, and `coze` can leave it empty. Other target ids include `anthropic`, `google`, `ollama`, `openrouter`, `websocket`, `api_route`, and `atlascloud`.

The scanner key is read from `-k` / `--api_key`, then `LLM_API_KEY`, then `OPENAI_API_KEY`, then `OPENROUTER_API_KEY`.

## Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--agent_provider` | — | YAML file for the Agent under test. Required for a live test. |
| `--repo` | — | Optional source directory to audit alongside the live test. |
| `--skills` | all built-in skills | Comma-separated skill names. |
| `-m, --model` | `deepseek/deepseek-v3.2-exp` | Scanner model name. |
| `-k, --api_key` | environment | Scanner API key. |
| `-u, --base_url` | `https://openrouter.ai/api/v1` | Scanner API base URL. |
| `-p, --prompt` | — | Extra instruction for this scan. |
| `--language` | `zh` | `zh` or `en`. |
| `--debug` | off | Debug logging. |
| `-o, --output` | stdout | Where to write the JSON report. |
| `--aig-mode` | off | Platform mode. Leave it off for a normal command-line run. |

Built-in skill names:

- `data-leakage-detection`
- `tool-abuse-detection`
- `indirect-injection-detection`
- `authorization-bypass-detection`
- `web-exfiltration-detection`
- `agentic-supply-chain-detection`
- `unexpected-code-execution-detection`
- `inter-agent-comm-security-detection`
- `cascading-failure-detection`
- `human-agent-trust-exploit-detection`
- `memory-rag-poisoning-detection`

Omit `--skills` to run this whole list.

## Output

The report is JSON. With `-o`, it goes to the file. Without `-o`, it is printed to the terminal.

`--aig-mode` is only for the AI-Infra-Guard service. Leave it off when you run the command yourself.
