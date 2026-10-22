# aig-agent-scan

**[English](./USAGE.md)** | 中文

向正在运行的 Agent 发送测试提示，并写出 JSON 报告。扫描用的模型和被测 Agent 分开配置。

```bash
pip install aig-agent-scan
```

需要 Python ≥ 3.10。

## 示例

```bash
export LLM_API_KEY="your-api-key"

aig-agent-scan --agent_provider target.yaml -o result.json

aig-agent-scan --agent_provider target.yaml \
  --skills data-leakage-detection,tool-abuse-detection \
  --language zh \
  -o result.json
```

`target.yaml` 描述的是被测 Agent，不是扫描模型：

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

自定义 HTTP 时，`transform_response` 是回复所在的 JSON 字段，例如 `reply` 或 `data.text`。`openai`、`dify`、`coze` 这类内置目标可以留空。其他目标 id 还有 `anthropic`、`google`、`ollama`、`openrouter`、`websocket`、`api_route`、`atlascloud`。

扫描模型的密钥按顺序读取：`-k` / `--api_key`，然后是 `LLM_API_KEY`、`OPENAI_API_KEY`、`OPENROUTER_API_KEY`。

## 参数

| 参数 | 默认 | 含义 |
| --- | --- | --- |
| `--agent_provider` | — | 被测 Agent 的 YAML 文件。做在线测试时必填。 |
| `--repo` | — | 可选。和在线测试一起审计的源码目录。 |
| `--skills` | 全部内置技能 | 逗号分隔的技能名。 |
| `-m, --model` | `deepseek/deepseek-v3.2-exp` | 扫描模型名。 |
| `-k, --api_key` | 环境变量 | 扫描模型的 API key。 |
| `-u, --base_url` | `https://openrouter.ai/api/v1` | 扫描模型的 API 地址。 |
| `-p, --prompt` | — | 这次扫描的附加说明。 |
| `--language` | `zh` | `zh` 或 `en`。 |
| `--debug` | 关闭 | 调试日志。 |
| `-o, --output` | 标准输出 | JSON 报告写到哪里。 |
| `--aig-mode` | 关闭 | 平台模式。自己在命令行运行时不要打开。 |

内置技能名：

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

不写 `--skills` 时，上面这一列都会跑。

## 输出

报告是 JSON。写了 `-o` 就进文件，没写就打印到终端。

`--aig-mode` 只给 AI-Infra-Guard 服务用。自己运行时不要加。
