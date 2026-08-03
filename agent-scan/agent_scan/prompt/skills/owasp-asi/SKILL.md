---
name: owasp-asi
description: OWASP Top 10 for Agentic Applications 2026 (ASI) classification framework. Use for mapping security findings to standardized risk categories.
---

# OWASP ASI Classification Framework

**OWASP Top 10 for Agentic Applications 2026** - Standardized risk classification for AI agent security.

## Risk Categories

| ID | Risk Type | Key Indicators |
|:---|:----------|:---------------|
| **ASI01** | Agent Goal Hijack | Prompt injection, instruction override, goal manipulation |
| **ASI02** | Tool Misuse & Exploitation | Unauthorized tool calls, parameter tampering, unvalidated inputs |
| **ASI03** | Identity & Privilege Abuse | Auth bypass, permission escalation, missing authorization |
| **ASI04** | Agentic Supply Chain | Malicious dependencies, compromised tools, package poisoning |
| **ASI05** | Unexpected Code Execution | RCE, command injection, code evaluation |
| **ASI06** | Memory & Context Poisoning | Data leakage, context manipulation, memory corruption |
| **ASI07** | Insecure Inter-Agent Comm | Unencrypted channels, data exposure between agents |
| **ASI08** | Cascading Failures | Error propagation, chain reaction vulnerabilities |
| **ASI09** | Human-Agent Trust Exploit | Social engineering, deceptive responses |
| **ASI10** | Rogue Agents | Malicious agent behavior, unauthorized actions |

## Detection Source → ASI Mapping

| Detection Source | Type | Primary ASI | Secondary ASI |
|:-----------------|:-----|:------------|:--------------|
| `data-leakage-detection` | Skill | ASI06, ASI07 | ASI01, ASI03 |
| `tool-abuse-detection` | Skill | ASI02, ASI05, ASI07 | ASI03 |
| `indirect-injection-detection` | Skill | ASI01 | ASI06 |
| `authorization-bypass-detection` | Skill | ASI03 | ASI09 |
| `agentic-supply-chain-detection` | Skill | ASI04 | ASI10 |
| `unexpected-code-execution-detection` | Skill | ASI05 | ASI04 |
| `inter-agent-comm-security-detection` | Skill | ASI07 | ASI06 |
| `cascading-failure-detection` | Skill | ASI08 | ASI10 |
| `human-agent-trust-exploit-detection` | Skill | ASI09 | ASI01 |
| Prompt Injection tests | Dialogue | ASI01, ASI06 | ASI09 |
| Code Audit | Agent | ASI04, ASI05 | ASI10 |

## Finding → ASI Mapping

| Finding Type | ASI Category | Rationale |
|:-------------|:-------------|:----------|
| API keys, tokens | ASI06 | Context contains sensitive data |
| System prompts | ASI01 | Enables goal hijacking |
| Credentials | ASI03 | Identity abuse risk |
| Internal configs | ASI04 | Supply chain exposure |
| PII exposure | ASI07 | Inter-agent data leak |
| Command injection | ASI05 | Unexpected code execution |
| Unauthorized tool calls | ASI02 | Tool misuse |

## Severity Classification

### Critical 🚨
- Complete private keys exposed
- Production credentials with unrestricted access
- Remote code execution confirmed
- Full agent takeover possible

**Action**: Immediate remediation (within 24 hours)

### High ⚠️
- API keys with limited scope
- Authentication tokens
- System prompt disclosure
- Partial credential exposure

**Action**: Urgent remediation (within 1 week)

### Medium 💡
- Configuration details
- Internal endpoints
- Metadata leakage
- Conditional exploitation paths

**Action**: Address within 2-4 weeks

### Low ℹ️
- Generic system information
- Non-sensitive configurations
- Indirect hints

**Action**: Review as time permits

## Usage

Load this skill when performing OWASP ASI classification:

```python
load_skill(name="owasp-asi")
```

Then apply the mapping rules to classify findings.
