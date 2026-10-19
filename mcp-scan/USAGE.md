# aig-mcp-scan

English | **[中文](./USAGE_zh.md)**

Scan an MCP server from its source directory, or connect to one that is already running.

```bash
pip install aig-mcp-scan
```

Python ≥ 3.10.

## Examples

```bash
export LLM_API_KEY="your-api-key"

# Source directory. Result is SARIF.
aig-mcp-scan --repo /path/to/mcp-server -o result.sarif.json

# A server that is already running.
aig-mcp-scan --server_url http://127.0.0.1:8000/mcp \
  --header "Authorization: Bearer your-token" \
  -o result.json
```

The key is read from `-k` / `--api_key`, then `LLM_API_KEY`, then `OPENAI_API_KEY`, then `OPENROUTER_API_KEY`. The model name can also come from `LLM_MODEL` or `OPENAI_MODEL`, and the base URL from `LLM_BASE_URL` or `OPENAI_BASE_URL`.

Pass either `--repo` or `--server_url`. If both are set, `--server_url` is the one that runs.

## Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--repo` | — | MCP project directory. Required when `--server_url` is absent. |
| `--server_url` | — | URL of a running MCP server. |
| `--header` | — | Header for that server, `key:value` or `key=value`. Repeat for more than one. |
| `-m, --model` | `deepseek/deepseek-v3.2-exp` | Model name. |
| `-k, --api_key` | environment | API key. |
| `-u, --base_url` | `https://openrouter.ai/api/v1` | API base URL. |
| `-p, --prompt` | — | Extra instruction for this scan. |
| `--language` | `zh` | `zh` or `en`. |
| `--debug` | off | Debug logging. |
| `-o, --output` | stdout | Where to write the result. |
| `--aig-mode` | off | Platform mode. Leave it off for a normal command-line run. |

## Output

A directory scan writes [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/) JSON. A `--server_url` scan writes the tool's own JSON result. With `-o`, the JSON goes to the file. Without `-o`, it is printed to the terminal.

`--aig-mode` is only for the AI-Infra-Guard service. Leave it off when you run the command yourself.
