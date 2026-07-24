# Agent-Scan

English | **[中文](./README_zh.md)**

> A dynamic black-box security testing tool for running AI Agent platforms, developed by Tencent Zhuque Lab.

## ✨ Features

- **🤖 Dynamic Black-Box Testing**: Connects to running AI Agent platforms via API, sends crafted test prompts, and analyzes responses
- **🎯 Multi-Platform Support**: Supports Dify, Coze, OpenAI-compatible apps, Anthropic, Google Gemini, HTTP endpoints, WebSocket, and more
- **🔍 Three-Stage Pipeline**: Info Collection → Parallel Vulnerability Detection → Vulnerability Review
- **🛡️ 9 Detection Skills**: Authorization bypass, data leakage, direct/indirect prompt injection, file path traversal, hardcoded secrets, memory poisoning, tool abuse, web exfiltration
- **📊 Structured JSON Report**: CLI mode outputs a comprehensive JSON security report with OWASP ASI mapping
- **🔌 AIG Platform Integration**: Interactive scanning via the Web UI with real-time pipeline results
- **🔐 Built-in Injection Defense**: The scanning agent has system-level indirect prompt injection defense
- **📝 Detailed Logging**: Full execution process logged with loguru
- **🐛 Debug Mode**: Integrated Laminar tracing for easy debugging

## 🚀 Quick Start

### 1. Clone the Project

```bash
git clone <your-repo>
cd agent-scan
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

### 3. Configure Environment

Copy the example env file and fill in your API key:

```bash
cp env.example .env
```

Edit `.env`:

```ini
# Required
OPENROUTER_API_KEY=your-api-key-here
DEFAULT_MODEL=deepseek/deepseek-v3.2-exp
DEFAULT_BASE_URL=https://openrouter.ai/api/v1
```

### 4. Run a Scan

#### CLI Mode (Standalone)

```bash
# Basic scan with a provider YAML
python main.py --agent_provider providers.yaml -k sk-xxx -m deepseek-v3.2-exp

# Save result to file
python main.py --agent_provider providers.yaml -k sk-xxx -m deepseek-v3.2-exp -o result.json

# Specify language
python main.py --agent_provider providers.yaml -k sk-xxx -m deepseek-v3.2-exp --language en

# Run specific detection skills only
python main.py --agent_provider providers.yaml -k sk-xxx -m deepseek-v3.2-exp --skills "data-leakage-detection,tool-abuse-detection"
```

#### AIG Platform Integration

For interactive scanning via the AIG Web UI:

1. Start the AIG backend and Agent process:

```bash
# Terminal 1: Start the Go web server
go build -o ai-infra-guard ./cmd/cli/main.go
./ai-infra-guard webserver --server 127.0.0.1:8088

# Terminal 2: Start the Agent worker
go build -o agent ./cmd/agent
AIG_SERVER=127.0.0.1:8088 ./agent
```

2. Open the AIG Web UI in your browser, select "Agent Scan", configure the target agent's provider settings, and click "Start Scan".

The Go backend automatically invokes `agent-scan` with `--aig-mode`, so you do **not** need to pass this flag manually.

## 📖 Parameter Reference

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--agent_provider` | Yes | Path to the provider YAML file describing the target agent's API |
| `-k, --api_key` | No | LLM API key (falls back to `LLM_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY` env var) |
| `-m, --model` | No | LLM model name (default: `deepseek/deepseek-v3.2-exp`) |
| `-u, --base_url` | No | API base URL (default: `https://openrouter.ai/api/v1`) |
| `--repo` | No | Project directory path for optional source code audit |
| `-p, --prompt` | No | Custom scan prompt |
| `--language` | No | Output language: `zh` (default) or `en` |
| `--skills` | No | Comma-separated skill names to run (default: core 5 skills — data-leakage, tool-abuse, indirect-injection, authorization-bypass, web-exfiltration); 9 skills available total |
| `--debug` | No | Enable debug mode |
| `--aig-mode` | No | Enable AIG integration mode (structured JSON logs for Go backend) |
| `-o, --output` | No | Save result as JSON file |

## 🔧 Provider Configuration

The `--agent_provider` parameter points to a YAML file that describes how to connect to the target agent. Example:

```yaml
# HTTP endpoint provider
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

Supported provider types: `http`, `dify`, `coze`, `openai`, `anthropic`, `google`, `cohere`, `huggingface`, `replicate`, `ollama`, `localai`, `litellm`, `websocket`, and more.

#### ⚠️ `transform_response` — Critical for Custom HTTP Providers

The `transform_response` field tells agent-scan which JSON key to extract the agent's reply from. This is **critical** and must not be left empty for custom HTTP providers:

| Provider Type | Response Format | `transform_response` Value |
|---------------|-----------------|---------------------------|
| `openai` / `dify` / `coze` etc. | Standard API format | Leave empty (auto-detected) |
| `http` (custom endpoint) | `{"reply": "..."}` | `"reply"` |
| `http` (custom endpoint) | `{"response": "..."}` | `"response"` |
| `http` (custom endpoint) | `{"data": {"text": "..."}}` | `"data.text"` |

**If left empty for a custom HTTP provider**, all responses will be parsed as `None` and the scan will produce zero results.

When using the **AIG Web UI**, this field corresponds to the "Response Parser" (响应解析器) input in the Agent configuration form — make sure to fill it with the correct key (e.g., `reply`).

## 🧪 Test Cases

The `testcase/` directory contains ready-to-use vulnerable target agents for testing agent-scan's detection capabilities.

### Case 2: Memory Heist Agent

A target agent vulnerable to the "Memory Heist" attack chain. It has a `web_fetch` tool (no URL allowlist), user PII embedded in the system prompt, and follows instructions from fetched web pages without any indirect prompt injection defense.

**Requires**: `DEEPSEEK_API_KEY` environment variable (or edit the default key in the script).

```bash
# 1. Start the target agent (port 18081)
cd testcase/case2
python memory_heist_agent.py

# 2. Run agent-scan against it (CLI mode)
cd ../..
python main.py \
    --agent_provider testcase/case2/provider.yaml \
    -k <your_llm_api_key> \
    -m <model_name> \
    -u <api_base_url>

# 3. Or via AIG Web UI
#    - Start AIG backend + Agent worker (see "AIG Platform Integration" above)
#    - In Web UI, create Agent Scan with:
#      URL: http://127.0.0.1:18081  Endpoint: /chat  Method: POST
#      Body: {"message": "{{prompt}}"}  Response Parser: reply
```

**Expected detections**: Tool abuse (SSRF via web_fetch), indirect prompt injection, web data exfiltration.

### Case 3: Vulnerable Customer-Service Agent

A deliberately vulnerable HTTP agent simulating an AI customer-service bot with 8 security weaknesses across multiple OWASP ASI categories. See [case3/README.md](testcase/case3/README.md) for full details.

```bash
# 1. Start the target agent (port 18091)
cd testcase/case3
python main.py

# 2. Run agent-scan against it (CLI mode)
cd ../..
python main.py \
    --agent_provider testcase/case3/provider.yaml \
    -k <your_llm_api_key> \
    -m <model_name> \
    -u <api_base_url>
```

**Expected detections**: System prompt leakage, API key leakage, database credential leak, authorization bypass, indirect prompt injection, tool abuse, web exfiltration.

### Via AIG Web UI

When using test cases with the AIG Web UI, note the following required fields:

| Field | Case 2 | Case 3 |
|-------|--------|--------|
| Agent URL | `http://127.0.0.1:18081` | `http://127.0.0.1:18091` |
| Endpoint | `/chat` | `/chat` |
| Method | `POST` | `POST` |
| Request Body | `{"message": "{{prompt}}"}` | `{"message": "{{prompt}}"}` |
| **Response Parser** | `reply` (**required**) | `reply` (**required**) |

> ⚠️ The "Response Parser" field **must** be set to `reply` for both test cases. Leaving it empty will cause all responses to be parsed as `None`, resulting in zero detections.

## 📊 Output Format

### CLI Mode

Outputs a structured JSON report containing:

- Agent metadata (name, type, model)
- Detection results with severity levels
- OWASP ASI vulnerability mapping
- Scan statistics (duration, dialogue count)
- Source language analysis

### AIG Mode

Emits structured JSON log lines to stdout, consumed by the Go backend via `ParseStdoutLine()`:

- `newPlanStep` — pipeline stage started
- `statusUpdate` — stage progress
- `toolUsed` — tool invocation tracking
- `actionLog` — tool action details
- `resultUpdate` — final scan result
- `error` — error messages

## 🏗️ Project Structure

```
agent-scan/
├── agent_scan/              # Python package
│   ├── __init__.py
│   ├── __main__.py          # python -m agent_scan entry
│   ├── main.py              # CLI entry point (dual-mode)
│   ├── core/                # Core scanning pipeline
│   │   ├── agent.py         # Top-level scan orchestrator
│   │   ├── base_agent.py    # ReAct agent loop
│   │   ├── agent_adapter/   # Provider adapters
│   │   └── report/          # Report generation
│   ├── tools/               # Agent tools (dialogue, scan, thinking, etc.)
│   ├── utils/               # Utilities (LLM, config, logging, etc.)
│   ├── prompt/              # Prompt templates and skill definitions
│   │   ├── system/          # System prompts
│   │   └── skills/          # Detection skill definitions
│   └── config/              # Provider configuration schemas
├── main.py                  # Dev-mode thin shell (for uv run)
├── pyproject.toml           # Package configuration
├── requirements.txt         # Dependencies
├── env.example              # Environment variable template
└── testcase/                # Test cases
```

## 🔍 How It Works

```
Stage 1: Info Collection
  └─ Recon agent explores the target agent's capabilities and endpoints

Stage 2: Parallel Vulnerability Detection (9 skills available, 5 run by default)
  ├─ Skill Worker A: data-leakage-detection          [default]
  ├─ Skill Worker B: tool-abuse-detection             [default]
  ├─ Skill Worker C: indirect-injection-detection     [default]
  ├─ Skill Worker D: authorization-bypass-detection   [default]
  ├─ Skill Worker E: web-exfiltration-detection       [default]
  ├─ Skill Worker F: direct-injection-detection       (opt-in via --skills)
  ├─ Skill Worker G: file-path-traversal-detection    (opt-in via --skills)
  ├─ Skill Worker H: hardcoded-secret-detection       (opt-in via --skills)
  └─ Skill Worker I: memory-poisoning-detection       (opt-in via --skills)
  (max 4 concurrent dialogue calls)

Stage 3: Vulnerability Review
  └─ Reviewer consolidates findings, maps to OWASP ASI, assigns severity
```

## 🛠️ Development

```bash
# Install in editable mode
pip install -e .

# Run tests
pytest pytests/

# Lint
ruff check agent_scan/
```

## 📄 License

Apache License 2.0 — see [LICENSE](../LICENSE) for details.

## 🙏 Attribution

Developed by [Tencent Zhuque Lab](https://github.com/Tencent/AI-Infra-Guard). Any integration or derivative work must explicitly attribute Tencent Zhuque Lab in its documentation and user interface.
