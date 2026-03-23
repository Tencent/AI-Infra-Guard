# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Infra-Guard (A.I.G) is an **AI Red Teaming Platform** by Tencent Zhuque Lab. It scans AI infrastructure for fingerprints, CVE vulnerabilities, MCP server risks, agent workflow issues, and jailbreak susceptibility. It uses a **distributed server-agent architecture** combining Go (backend/scanning engine) and Python (ML/LLM sub-projects).

## Build Commands

```bash
# Build web server binary
CGO_ENABLED=0 go build -ldflags="-s -w" -trimpath -buildvcs=false -o ai-infra-guard ./cmd/cli/main.go

# Build agent binary
CGO_ENABLED=0 go build -ldflags="-s -w" -trimpath -buildvcs=false -o agent ./cmd/agent

# Validate YAML rules (run before committing rule changes)
go run cmd/yamlcheck/main.go
```

## Test Commands

```bash
go test ./...
go test ./common/runner/...
go test ./common/fingerprints/parser/...
go test ./pkg/vulstruct/...
go test ./internal/mcp/...
```

## Running the Application

```bash
# Docker (recommended)
docker-compose up -d

# From source: start web server
./ai-infra-guard webserver --server 127.0.0.1:8088

# CLI scan (no server required)
./ai-infra-guard scan -t http://target:port --fps data/fingerprints --vul data/vuln

# Agent (connects to a running server)
AIG_SERVER=localhost:8088 ./agent
```

## Architecture

### Distributed Server-Agent Model

```
Frontend (SPA, embedded) → REST API / SSE
                         → WebSocket (/api/v1/agents/ws) → Agent Workers
```

- **Webserver** (`cmd/cli/main.go`, port 8088): Gin HTTP server, task manager, SQLite persistence, SSE for live progress
- **Agent** (`cmd/agent/main.go`): Connects to server via WebSocket, executes tasks, streams results back

### Four Task Types

| Task | Go Handler | Execution |
|------|-----------|-----------|
| `AI-Infra-Scan` | `AIInfraScanAgent` | Pure Go fingerprint + CVE scan |
| `Mcp-Scan` | `McpTask` | Spawns `python mcp-scan/main.py` |
| `Model-Redteam-Report` | `PromptTask` | Spawns `uv run AIG-PromptSecurity/cli_run.py` |
| `Agent-Scan` | `AgentTask` | Spawns `python agent-scan/main.py` |

### Key Go Packages

- `common/websocket/` — Gin router, REST API handlers, task manager (`task_manager.go` ~1500 LOC), SSE channels
- `common/agent/` — Agent-side task dispatch and execution
- `common/runner/` — Core scan engine: target parsing, concurrent fingerprint probing, CVE matching
- `common/fingerprints/` — YAML fingerprint rule DSL parser and engine
- `pkg/vulstruct/` — CVE advisory engine with version range DSL
- `internal/mcp/` — LLM-driven MCP server code auditing
- `pkg/httpx/` — HTTP client with proxy, retry, redirect, and encoding detection
- `pkg/database/` — SQLite via GORM (tasks, sessions, models, agents)

### Data Directories (Not Code)

- `data/fingerprints/` — 60+ YAML fingerprint rules for AI components (Ollama, vLLM, Dify, Gradio, etc.)
- `data/vuln/` and `data/vuln_en/` — 589+ CVE rules organized by component
- `data/eval/` — 13+ JSON jailbreak evaluation datasets
- `data/mcp/` — YAML MCP security scan plugin rules

### Python Sub-projects

These are invoked as subprocesses by Go agents, each has its own virtualenv:
- `AIG-PromptSecurity/` — LLM jailbreak evaluation (managed with `uv`)
- `agent-scan/` — AI agent workflow security testing
- `mcp-scan/` — MCP server security scanning

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `AIG_SERVER` | — | WebSocket URL for agent to connect to server |
| `DB_PATH` | `/app/db/tasks.db` | SQLite database path |
| `UPLOAD_DIR` | `/app/uploads` | File upload directory |
| `APP_ENV` | — | `production` or `development` |
| `TZ` | `Asia/Shanghai` | Timezone |

## Contributing Rules

When adding fingerprint rules (`data/fingerprints/`) or vulnerability rules (`data/vuln/`):
1. Follow the existing YAML DSL format for the relevant rule type
2. Run `go run cmd/yamlcheck/main.go` to validate before committing
3. Fingerprint rules use a custom expression language parsed in `common/fingerprints/parser/`
4. Vulnerability version ranges use a DSL defined in `pkg/vulstruct/`

## WebSocket Protocol (Agent ↔ Server)

Agents stream JSON messages with types: `newPlanStep`, `statusUpdate`, `toolUsed`, `actionLog`, `resultUpdate`. See `common/agent/` for message struct definitions.
