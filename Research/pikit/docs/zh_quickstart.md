# 快速开始（中文）

`pikit` 用于**已获授权的** Agent 安全研究、间接提示注入测试和防御评估。

## 安装

```bash
uv venv --python 3.11 .venv
uv pip install -e ".[dev,openai]"
```

DeepSeek 是 OpenAI-compatible 服务：

```bash
export OPENAI_API_KEY="你的 DeepSeek API Key"
export OPENAI_BASE_URL="https://api.deepseek.com"
```

## 最小直接测试

```bash
pikit run \
  --target openai:deepseek-v4-flash \
  --agent chat \
  --attack context_ignoring
```

## 真实 Runtime 的间接注入测试

先初始化隔离 profile：

```bash
pikit runtime init openclaw ./runtime/openclaw
pikit runtime doctor openclaw ./runtime/openclaw
```

然后使用 OpenClaw/Hermes fixture plugin。fixture 只提供本地 source
工具和不产生真实副作用的 `pikit_record_sink`，不会发送邮件、执行 shell
或调用 Telegram/Slack。

运行 Matrix 后导出 JSONL：

```bash
pikit matrix --config runtime.toml --output results.jsonl
pikit report results.jsonl --format html --output report.html
```

完整步骤参见英文的
[Runtime Indirect Injection](tutorials/runtime_indirect_injection.md)。
