# A.I.G × OpenClaw — AI Security Scanning in One Chat Message

[中文版](./README.zh-CN.md)

Invoke all [A.I.G (AI-Infra-Guard)](https://github.com/Tencent/AI-Infra-Guard/) scanning capabilities directly from an OpenClaw chat — no A.I.G Web UI needed.

> **Prerequisite**: A.I.G service is deployed (local or remote).

### Install

```bash
clawhub install aig-scanner
```

Alternative:

```text
Install this skill from source:
https://github.com/Tencent/AI-Infra-Guard/tree/main/skills/aig-scanner
```

ClawHub page:

<https://clawhub.ai/aigsec/aig-scanner>

### Usage

After installation, just chat:

**AI Infrastructure Scan** — detect CVEs and misconfigurations in AI services (Ollama, vLLM, Dify, etc.)

```
Scan http://localhost:11434 for AI vulnerabilities
```

**AI Tool / Skills Audit** — audit MCP Servers, Agent Skills, and similar projects

```
Scan https://github.com/org/repo for AI tool security issues
```

**AI Agent Scan** — test A.I.G-configured Agents for authorization bypass, prompt injection, data leakage

> Recommend configuring the Agent in A.I.G Web UI beforehand

```
Use A.I.G to scan agent demo-agent-id
```

**LLM Safety Check** — red-team test an LLM's jailbreak resistance

```
Use A.I.G to run a safety check on DeepSeek3.2
```

### Notes

- **Recommended install path**: use ClawHub.
- **Mainland China fallback**: if ClawHub fails with `Rate limit exceeded`, install from the source directory in this repository.
- **A.I.G URL**: configure `AIG_BASE_URL` on first install. This is required. Examples:
  - `http://127.0.0.1:8088/`
  - `https://aig.example.com/`
- **Auth**: configure an API Key if A.I.G authentication is enabled; defaults to empty.
- **AI Tool / Skills Scan**: requires an analysis model (model name, API key, base URL) — just tell OpenClaw on first use.
- **LLM Safety Check**: requires both the target model and a separate evaluator model configuration. Provide target/eval model name, API key, and base URL.
- **Agent Scan**: scans Agents already configured on the A.I.G platform; does not support parameter submission yet.

---

Powered by Tencent Zhuque Lab [A.I.G](https://github.com/Tencent/AI-Infra-Guard)
