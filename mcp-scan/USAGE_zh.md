# aig-mcp-scan

**[English](./USAGE.md)** | 中文

扫描 MCP Server 的源码目录，或连接一个已经在运行的服务。

```bash
pip install aig-mcp-scan
```

需要 Python ≥ 3.10。

## 示例

```bash
export LLM_API_KEY="your-api-key"

# 扫源码目录，结果是 SARIF
aig-mcp-scan --repo /path/to/mcp-server -o result.sarif.json

# 扫已经跑起来的服务
aig-mcp-scan --server_url http://127.0.0.1:8000/mcp \
  --header "Authorization: Bearer your-token" \
  -o result.json
```

密钥按顺序读取：`-k` / `--api_key`，然后是 `LLM_API_KEY`、`OPENAI_API_KEY`、`OPENROUTER_API_KEY`。模型名还可以来自 `LLM_MODEL` 或 `OPENAI_MODEL`，接口地址来自 `LLM_BASE_URL` 或 `OPENAI_BASE_URL`。

`--repo` 和 `--server_url` 二选一。两个都写时，实际执行的是 `--server_url`。

## 参数

| 参数 | 默认 | 含义 |
| --- | --- | --- |
| `--repo` | — | MCP 项目目录。没有 `--server_url` 时必填。 |
| `--server_url` | — | 正在运行的 MCP 服务地址。 |
| `--header` | — | 发给该服务的请求头，`key:value` 或 `key=value`。多个就重复写。 |
| `-m, --model` | `deepseek/deepseek-v3.2-exp` | 模型名。 |
| `-k, --api_key` | 环境变量 | API key。 |
| `-u, --base_url` | `https://openrouter.ai/api/v1` | API 地址。 |
| `-p, --prompt` | — | 这次扫描的附加说明。 |
| `--language` | `zh` | `zh` 或 `en`。 |
| `--debug` | 关闭 | 调试日志。 |
| `-o, --output` | 标准输出 | 结果写到哪里。 |
| `--aig-mode` | 关闭 | 平台模式。自己在命令行运行时不要打开。 |

## 输出

扫目录时写出 [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/) JSON。`--server_url` 写出工具自己的 JSON。写了 `-o` 就进文件，没写就打印到终端。

`--aig-mode` 只给 AI-Infra-Guard 服务用。自己运行时不要加。
