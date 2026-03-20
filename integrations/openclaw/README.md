# AIG × OpenClaw — AI Security Scanning in One Chat Message

[中文版](./README.zh-CN.md)

Invoke all [AIG (AI-Infra-Guard)](https://github.com/Tencent/AI-Infra-Guard/) scanning capabilities directly from an OpenClaw chat — no AIG Web UI needed.

> **Prerequisite**: AIG service is deployed (local or remote).

### Install (pick one, tell OpenClaw)

```
# Skill edition (recommended) — lightweight, zero build
Install and enable AIG Scan Skill
Download: https://github.com/Tencent/AI-Infra-Guard/raw/v4/integrations/openclaw/aig-scan-skill.tgz

# Plugin edition — background monitoring + persistent config
Install and enable AIG Scan Plugin
Download: https://github.com/Tencent/AI-Infra-Guard/raw/v4/integrations/openclaw/aig-scan-plugin.tgz
```

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

**AI Agent Scan** — test AIG-configured Agents for authorization bypass, prompt injection, data leakage

> Recommend configuring the Agent in AIG Web UI beforehand

```
Use AIG to scan agent demo-agent-id
```

**LLM Safety Check** — red-team test an LLM's jailbreak resistance

```
Use AIG to run a safety check on DeepSeek3.2
```

### Notes

- **AIG URL**: defaults to `http://localhost:8088`; no config needed for local AIG. For remote deployments, just tell OpenClaw the actual address.
- **Auth**: configure an API Key if AIG authentication is enabled; defaults to empty.
- **AI Tool / Skills Scan**: requires an analysis model (model name, API key, base URL) — just tell OpenClaw on first use.
- **Agent Scan**: scans Agents already configured on the AIG platform; does not support parameter submission yet.

---

Powered by Tencent Zhuque Lab [A.I.G](https://github.com/Tencent/AI-Infra-Guard)
