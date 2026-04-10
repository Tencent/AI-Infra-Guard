# AI-Infra-Guard Architecture Evolution

This document describes the architectural evolution of A.I.G (AI-Infra-Guard) across three major stages: v0.1, v2.6, and v3.6.0+. It focuses on responsibility boundaries, capability growth, and runtime topology at each stage.

---

## v0.1 — Single-Binary Infrastructure Scanner

**Purpose**: Lightweight, zero-dependency AI infrastructure vulnerability scanner. Ship fast, scan fast.

### Capability Summary

- Network-based fingerprinting of AI services (Ollama, vLLM, Dify, etc.)
- Rule-driven CVE/GHSA vulnerability matching against detected components
- CLI-first task dispatch; WebUI for result visualization

### Technical Stack & Delivery

| Aspect | Detail |
|---|---|
| Language | Go |
| Delivery | Single compiled binary |
| Entry point | `cmd/cli` |
| Config | CLI flags / YAML rule files |

### Architecture Layers

```
┌────────────────────────────────────────┐
│         Entry & Interaction            │
│    CLI (cmd/cli)  ·  WebUI (static)    │
├────────────────────────────────────────┤
│          Task Scheduling               │
│   Target splitting · Concurrency ctl   │
├────────────────────────────────────────┤
│           Rule Engine                  │
│  Fingerprint match · Vuln scoring      │
├────────────────────────────────────────┤
│         Probe Execution                │
│  HTTP probes · Service detection       │
├────────────────────────────────────────┤
│           Rule Data Layer              │
│  data/fingerprints/  · data/vuln/      │
└────────────────────────────────────────┘
```

### Runtime Flow

```
CLI/WebUI
  └─▶ Scheduler (runner.go)
        └─▶ Fingerprint engine  ──▶  Version extraction
              └─▶ Vuln matcher   ──▶  Structured result output
```

---

## v2.6 — Dual-Engine: Infrastructure Scan + MCP Code Analysis

**Purpose**: Extend v0.1 with MCP Server security analysis. A single binary now ships both a rule-driven scanner and an LLM-assisted code auditor.

### New Capabilities

- MCP Server code security analysis (static rules + LLM reasoning)
- Unified CLI sub-commands (`scan` / `mcp`)
- Integrated WebUI covering both scan types
- Task management API via WebSocket/REST

### Technical Stack & Delivery

| Aspect | Detail |
|---|---|
| Language | Go |
| Delivery | Single compiled binary |
| New modules | `internal/mcp/`, `common/websocket/` |
| LLM integration | OpenAI-compatible API (`common/utils/models/openai.go`) |

### Architecture Layers

```
┌────────────────────────────────────────────────┐
│              Entry & Interaction               │
│   CLI sub-commands  ·  WebUI  ·  REST/WS API   │
├──────────────────────┬─────────────────────────┤
│   AI Infra Scan      │   MCP Security Analysis  │
│  Rule-driven engine  │  Agent-driven code audit │
├──────────────────────┴─────────────────────────┤
│         Task & Utility Layer                   │
│  Orchestration · Result aggregation · Utils    │
├────────────────────────────────────────────────┤
│           Rule & Data Layer                    │
│  Fingerprints · Vuln rules · MCP rule YAMLs    │
└────────────────────────────────────────────────┘
```

### Runtime Flow

```
CLI
  ├─ scan ──▶ Rule Engine ──▶ Vuln Matcher ──▶ Report
  └─ mcp  ──▶ MCP Agent   ──▶ Code Audit   ──▶ Risk Report

WebUI / REST API
  └─▶ Unified task interface ──▶ Result display
```

---

## v3.6.0+ — Multi-Module AI Red Teaming Platform

**Purpose**: Platform-scale AI security system. Go + Python hybrid. Three coordinated security modules with hot-pluggable scan engines and multi-deployment profiles (on-prem, SaaS, open-source).

### New Capabilities

- **Prompt Security Evaluation** (`AIG-PromptSecurity/`): LLM jailbreak red-teaming with 10+ attack strategies (encoding, stego, role-play, etc.)
- **Agent Scan** (`common/agent/`): Multi-agent automated security assessment of AI agent workflows (Dify, Coze, etc.) — covers indirect prompt injection, SSRF, system prompt leakage
- **MCP Scan v2** (`mcp-scan/`): Rewritten as standalone Python agent with dynamic verification, code audit pipeline, and multi-stage LLM reasoning
- Docker Compose one-click deployment; multi-image architecture
- Plugin/feature extension framework

### Technical Stack & Delivery

| Aspect | Detail |
|---|---|
| Languages | Go (core) + Python (agents, eval) |
| Delivery | Docker images + Compose, or single binary |
| Core service | `cmd/` + `common/` + `internal/` (Go) |
| MCP scan agent | `mcp-scan/` (Python, standalone) |
| Prompt eval | `AIG-PromptSecurity/` (Python, standalone) |
| LLM integration | OpenAI-compatible; configurable per module |

### Architecture Layers

```
┌──────────────────────────────────────────────────────────────┐
│                   Deployment Profiles                        │
│    On-prem (SSO/intranet)  ·  SaaS  ·  Open-source release  │
├──────────────────────────────────────────────────────────────┤
│                    Entry & Orchestration                     │
│         CLI / WebUI / REST API / WebSocket                   │
│              Agent runtime  ·  Task scheduler                │
├───────────────────┬───────────────────┬──────────────────────┤
│  AI Infra Scan    │  MCP Security Scan │  Prompt Eval         │
│  Go rule engine   │  Python agent +   │  Python DeepTeam +   │
│  Fingerprint +    │  static rules +   │  10+ attack types    │
│  Vuln matching    │  LLM verification │  Dataset-driven      │
├───────────────────┴───────────────────┴──────────────────────┤
│                  Task & Report Layer                         │
│     Task scheduling · Result aggregation · PDF report gen    │
├──────────────────────────────────────────────────────────────┤
│                   Rule & Data Layer                          │
│  data/fingerprints/  ·  data/vuln(_en)/  ·  data/mcp/       │
│  data/eval/          ·  MCP rule YAMLs   ·  Eval datasets    │
└──────────────────────────────────────────────────────────────┘
```

### Runtime Flow

```
WebUI / CLI / API
  └─▶ Task Scheduler (common/websocket/)
        ├─▶ AI Infra Scan (Go)
        │     └─▶ Fingerprint engine ──▶ Vuln rules ──▶ CVE report
        │
        ├─▶ MCP Scan (Python agent)
        │     └─▶ Code audit ──▶ Static rules ──▶ LLM verification ──▶ Risk report
        │
        ├─▶ Agent Scan (Go agent)
        │     └─▶ Multi-agent pipeline ──▶ Injection/SSRF/leak tests ──▶ Report
        │
        └─▶ Prompt Eval (Python)
              └─▶ Attack generation ──▶ LLM target ──▶ Judge ──▶ Safety score
```

---

## Version Comparison

| Version | Core Capabilities | Tech Stack | Architecture Pattern |
|---|---|---|---|
| v0.1 | AI infra vuln scan + WebUI | Go single binary | Monolithic scanner, rule-driven |
| v2.6 | Infra scan + MCP code analysis | Go single binary | Dual-engine, unified WebUI |
| v3.6.0+ | Infra scan + MCP scan + Agent scan + Prompt eval | Go + Python, Docker | Platform, multi-module, pluggable engines |

---

## Key Design Decisions

**Rule-first, LLM-augmented**: Core detection remains deterministic (YAML fingerprint + vuln rules) for speed and consistency. LLM reasoning is layered on top for complex cases (MCP code audit, agent simulation).

**Language split by concern**: Go handles high-concurrency network probing and the web platform. Python handles LLM agent loops, evaluation frameworks, and ML-adjacent tooling.

**Data as source of truth**: All detection rules live in `data/` as version-controlled YAML. No rules are embedded in compiled binaries. This enables out-of-band rule updates and CI validation.

**Pluggable scan engines**: From v3.6.0+, each scan module (infra, MCP, agent, prompt) is independently deployable and versioned, connected through the task API.
