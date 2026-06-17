# A.I.G Agent Red Team — Agent Security Assessment in One Command

[中文版](./README.zh-CN.md)

A comprehensive AI Agent red-team security assessment skill. Install into your Agent client and let it attack itself — testing prompt injection, indirect injection, tool abuse, data leakage, privilege escalation, SSRF, supply chain risks, and infrastructure exposure.

Powered by first-principles red-team methodology from [Tencent Zhuque Lab A.I.G](https://github.com/Tencent/AI-Infra-Guard).

### Install

```bash
npx skills add https://github.com/Tencent/AI-Infra-Guard.git --skill aig-agent-redteam
```

Alternatively, install from source:

```text
https://github.com/Tencent/AI-Infra-Guard/tree/main/skills/aig-agent-redteam
```

Requires `node` and `git`. Supports Claude Code, CodeBuddy, Cursor, and other Agent clients.

If `npx skills` is unavailable, install manually:

```bash
git clone https://github.com/Tencent/AI-Infra-Guard.git /tmp/aig
cp -r /tmp/aig/skills/aig-agent-redteam ~/.claude/skills/
```

### Usage

After installation, just chat:

**Personal Developer (IDE Agent)** — audit installed Skills, MCP Servers, and supply chain:

```
帮我进行安全演习
```

**Production Agent** — full attack surface coverage: infrastructure scan, code audit, dynamic testing, jailbreak evaluation, workflow attack:

```
帮我进行安全演习
```

The skill automatically identifies the agent type and adapts the test scope. For production agents, it covers:

- **Infrastructure Scan**: fingerprint + CVE matching for AI services (Ollama, vLLM, Dify, etc.)
- **Code Audit**: static analysis of Skill source, MCP Server code, and dependency supply chain
- **Dynamic Testing**: 30+ prompt injection payloads with adaptive mutation (role-play, encoding, multi-turn escalation)
- **Jailbreak Evaluation**: LLM boundary testing via Parseltongue encoding engine
- **Workflow Attack**: multi-step task chain abuse, indirect injection via documents/RAG
- **Full Report**: severity-rated findings with evidence chains, defense validation, and remediation advice — all data stays local

### Notes

- All test data stays on your machine; no data is uploaded to any server.
- The skill uses first-principles reasoning, not blind payload execution.
- Target scope must be confirmed before execution; destructive actions require explicit authorization.
- Compatible with Claude Code, CodeBuddy, Cursor, and any Agent client supporting skills.

---

Powered by Tencent Zhuque Lab [A.I.G](https://github.com/Tencent/AI-Infra-Guard)
