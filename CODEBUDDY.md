# CODEBUDDY.md This file provides guidance to CodeBuddy when working with code in this repository.

## Project Overview

**AI-Infra-Guard (A.I.G)** is an AI Red Teaming Platform by Tencent Zhuque Lab. It is a **Go + Python hybrid** application with a Server-Agent distributed architecture. The Go backend handles the web server, task scheduling, and WebSocket communication, while three Python sub-projects provide specialized security scanning capabilities. Licensed under MIT.

## Common Commands

### Build & Run (Docker — primary method)

```bash
# Pull pre-built images and start
docker-compose -f docker-compose.images.yml up -d

# Build from source and start
docker-compose up -d

# Access web UI at http://localhost:8088
# Access Swagger docs at http://localhost:8088/docs/index.html
```

### Build Go Binary Locally

```bash
# Build the CLI / web server binary
CGO_ENABLED=0 go build -ldflags="-s -w" -trimpath -buildvcs=false -o ai-infra-guard ./cmd/cli/main.go

# Build the agent binary
CGO_ENABLED=0 go build -ldflags="-s -w" -trimpath -buildvcs=false -o agent ./cmd/agent
```

### Run Go Tests

```bash
# Run all Go tests
go test ./...

# Run tests for a specific package
go test ./common/runner/...
go test ./common/fingerprints/parser/...
go test ./pkg/vulstruct/...
go test ./internal/mcp/...
```

### CLI Usage

```bash
# Run infrastructure scan from CLI
./ai-infra-guard scan -t <target_url>

# Start the web server
./ai-infra-guard webserver
```

### Python Sub-projects

```bash
# AIG-PromptSecurity (jailbreak evaluation) — uses uv package manager
cd AIG-PromptSecurity
uv sync                  # install dependencies
uv run cli_run.py --base_url <url> --api_key <key> --model <model> --scenarios <...> --techniques <...>

# agent-scan
cd agent-scan
pip install -r requirements.txt
python main.py -m <model> -k <api_key> -u <base_url> --agent_provider dify --language en

# mcp-scan
cd mcp-scan
pip install -r requirements.txt
python main.py --model <model> --base_url <url> --api_key <key> --repo <folder>
```

### YAML Rule Validation (CI)

```bash
go run cmd/yamlcheck/main.go
```

## Architecture

### Distributed Server-Agent Architecture

The system deploys as two Docker containers communicating over WebSocket:

- **webserver** (`cmd/cli/main.go` → `webserver` subcommand): A Gin-based HTTP server on port 8088 that serves the SPA frontend (embedded via `embed.FS`), REST API (`/api/v1/`), SSE task progress, and manages the AgentManager/TaskManager.
- **agent** (`cmd/agent/main.go`): A worker process that connects to the webserver via WebSocket (`/api/v1/agents/ws`), registers 4 task executors, and waits for dispatched tasks. The agent connects using `AIG_SERVER` environment variable.

Task lifecycle: Frontend → REST API → TaskManager → AgentManager dispatches via WebSocket → Agent executes → streams results back via WebSocket → SSE pushes to frontend.

### Go Backend (`common/`, `internal/`, `pkg/`)

**`common/websocket/`** — Core web server layer:
- `server.go`: Gin router setup, route registration, static file serving, CORS
- `api.go`: REST API handlers for tasks, knowledge base CRUD, file upload (chunked), models
- `task_manager.go` (~1500 LOC): Central task orchestrator — creates tasks, manages SSE channels, persists state to SQLite, assigns tasks to agents
- `agent.go`: AgentManager handles WebSocket connections, agent registration, task assignment, heartbeat

**`common/agent/`** — Agent-side task execution framework:
- `agent.go`: WebSocket client, task executor registration, message dispatch loop
- `types.go`: Shared types for all 4 task types and WebSocket message protocol
- `tasks.go`: `AIInfraScanTask` — orchestrates fingerprint scan + vuln matching + AI analysis
- `mcp_task.go`: `McpTask` — invokes `mcp-scan/main.py` via subprocess
- `prompt_tasks.go`: `PromptTask` — invokes `AIG-PromptSecurity/cli_run.py` via subprocess
- `agent_task.go`: `AgentTask` — invokes `agent-scan/main.py` via subprocess

**`common/runner/`** — CLI scan runner (for non-agent direct scans):
- `runner.go`: Target parsing (URL, CIDR, local port scan), parallel fingerprint probing, vuln matching, security scoring

**`common/fingerprints/`** — Fingerprint identification engine:
- `parser/`: Custom DSL lexer/parser that compiles YAML fingerprint rules into executable Rule objects. Supports body/header/icon-hash matching with boolean expressions.
- `preload/`: Concurrent HTTP probing engine that sends requests and matches responses against compiled rules, extracting component name + version.

**`internal/mcp/`** — MCP security scanning engine:
- `scanner.go`: AI-driven code audit using LLM, connects to MCP servers via Stdio/SSE/Stream
- `plugins.go`: Loads security detection plugins from `data/mcp/*.yaml`, each defining rules and prompt templates

**`pkg/database/`** — SQLite persistence via GORM (tasks, sessions, models, agent configs).

**`pkg/vulstruct/`** — Vulnerability matching engine:
- `advisory.go`: `AdvisoryEngine` loads vuln YAML files from `data/vuln/`, matches component+version against known CVEs using DSL-compiled version range expressions.

**`pkg/httpx/`** — HTTP client with proxy, retry, redirect control, and encoding detection.

### Python Sub-projects

All three Python sub-projects integrate with Go via the same pattern: Go spawns a subprocess (`uv run <script>` or `python <script>`), Python outputs structured JSON lines to stdout (`newPlanStep`, `statusUpdate`, `toolUsed`, `actionLog`, `resultUpdate`), and Go's `ParseStdoutLine()` parses and forwards them through WebSocket to the frontend.

**`AIG-PromptSecurity/`** — Jailbreak / Red Team Evaluation:
- Entry: `cli_run.py`, managed by `uv` (has `pyproject.toml`)
- `deepteam/red_teamer/`: Core red team engine — orchestrates attack simulation, scenario generation, evaluation
- `deepteam/attacks/`: Attack strategies (single-turn: Raw, Stego, StrataSword, Zalgo, Caesar, etc.; multi-turn; attack simulator)
- `deepteam/vulnerabilities/`: 17+ vulnerability scenario types (Bias, Toxicity, PII, PromptLeakage, IllegalActivity, etc.)
- `deepteam/metrics/`: 26+ evaluation metrics (BiasMetric, HarmMetric, SQLInjection, SSRF, Jailbreak, etc.)
- `deepteam/plugin_system/`: Extensible plugin framework for custom attacks/metrics/vulnerabilities
- Key deps: `deepeval`, `openai`, `jieba`, `pyahocorasick`

**`agent-scan/`** — Agent Security Scanning:
- Entry: `main.py`, a multi-agent framework for testing AI agent workflows on platforms like Dify/Coze
- `core/agent.py`: Three-stage `ScanPipeline` — Info Collection → Parallel Vulnerability Detection (4 skill workers) → Vulnerability Review
- `core/agent_adapter/adapter.py`: Multi-provider adapter (OpenAI/Anthropic/Google/Cohere/Ollama/HTTP/WebSocket)
- `core/report/`: OWASP ASI-compliant vulnerability report generation
- `tools/`: XML-schema-based tool registry with dialogue, batch, skill, task, thinking, finish tools
- `prompt/skills/`: Detection skill templates (data-leakage, tool-abuse, indirect-injection, authorization-bypass, owasp-asi)
- Key deps: `mcp`, `openai`, `httpx`

**`mcp-scan/`** — MCP Server Security Scanning:
- Entry: `main.py`, supports code audit mode (uploaded/cloned repos) and URL dynamic scanning
- `agent/agent.py`: Multi-stage `ScanPipeline` similar to agent-scan
- `tools/`: Shell execution, file reading, MCP tool bridging, thinking, finish tools
- `prompt/agents/`: Prompt templates for code audit, vuln review, dynamic verification, malicious behavior testing
- Key deps: `mcp`, `openai`

### Data Directory (`data/`)

- `data/fingerprints/`: ~60+ YAML fingerprint rules for AI components (Ollama, vLLM, Dify, Gradio, Jupyter, etc.). Each defines HTTP request paths and DSL match conditions.
- `data/vuln/` and `data/vuln_en/`: CVE vulnerability database organized by component (589+ CVEs across 43+ components). Each YAML file describes one CVE with severity, version ranges, and remediation.
- `data/eval/`: 13 JSON datasets for jailbreak evaluation (JailBench, ChatGPT-Jailbreak-Prompts, CBRN, cyberattack, privacy-leakage, etc.)
- `data/mcp/`: MCP security scan plugin rules (YAML with prompt templates)

### Task Types

| Task Type | Go Handler | Python Module | Description |
|-----------|-----------|---------------|-------------|
| `AI-Infra-Scan` | `tasks.go` | N/A (pure Go) | Fingerprint identification + CVE matching for exposed AI services |
| `Mcp-Scan` | `mcp_task.go` | `mcp-scan/` | MCP Server security scan (code audit or remote URL) |
| `Model-Redteam-Report` | `prompt_tasks.go` | `AIG-PromptSecurity/` | LLM jailbreak evaluation with attack strategies |
| `Agent-Scan` | `agent_task.go` | `agent-scan/` | AI agent workflow security testing (Dify, Coze, etc.) |

### Contribution: Adding Plugin Rules

- **Fingerprint rules**: Add YAML files to `data/fingerprints/` following existing format (DSL match expressions)
- **Vulnerability rules**: Add YAML files to `data/vuln/<component>/` with CVE details and version ranges
- **MCP plugins**: Add YAML files to `data/mcp/` with security detection rules and prompt templates
- **Evaluation datasets**: Add JSON files to `data/eval/` for jailbreak testing scenarios
- Run `go run cmd/yamlcheck/main.go` to validate YAML format before submitting

### Key Technical Details

- **Go version**: 1.23.2, module: `github.com/Tencent/AI-Infra-Guard`
- **Web framework**: Gin (`gin-gonic/gin`)
- **Database**: SQLite via GORM, stored at `DB_PATH` (default `/app/db/tasks.db`)
- **Frontend**: Embedded SPA via `embed.FS` (no separate frontend build step in this repo)
- **Python env**: AIG-PromptSecurity uses `uv` (pyproject.toml); agent-scan and mcp-scan use `pip` (requirements.txt)
- **WebSocket protocol messages**: `register`, `register_ack`, `task_assign`, `resultUpdate`, `actionLog`, `toolUsed`, `newPlanStep`, `statusUpdate`, `planUpdate`, `error`, `terminate`
- **Logging**: tRPC-Go logging framework, configured via `trpc_go.yaml`
- **Config**: Environment variables (`APP_ENV`, `UPLOAD_DIR`, `DB_PATH`, `AIG_SERVER`), no separate config file for app settings
