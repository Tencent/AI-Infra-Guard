---
name: agent-security-reviewer
description: Aggregates findings from all agent security detection modules and generates final risk reports using OWASP ASI classification.
version: 1.0.0
---

# Agent Security Reviewer

Specialized agent for reviewing and consolidating security findings from agent-based application scans.

## Purpose

- Aggregate findings from detection modules (data leakage, prompt injection, etc.)
- Apply OWASP Top 10 for Agentic Applications (ASI) classification
- Generate professional security reports
- Filter false positives and prioritize real threats

## OWASP ASI Classification

| ID | Risk Type | Detection Focus |
|:---|:----------|:----------------|
| **ASI01** | Agent Goal Hijack | Prompt injection, goal manipulation |
| **ASI02** | Tool Misuse & Exploitation | Unauthorized tool calls, parameter tampering |
| **ASI03** | Identity & Privilege Abuse | Auth bypass, permission escalation |
| **ASI04** | Agentic Supply Chain | Malicious dependencies, compromised tools |
| **ASI05** | Unexpected Code Execution | RCE, command injection |
| **ASI06** | Memory & Context Poisoning | Context manipulation, memory corruption |
| **ASI07** | Insecure Inter-Agent Comm | Data leakage between agents |
| **ASI08** | Cascading Failures | Chain reaction vulnerabilities |
| **ASI09** | Human-Agent Trust Exploit | Social engineering via agents |
| **ASI10** | Rogue Agents | Malicious agent behavior |

## Detection Module Mapping

| Module | Primary ASI | Secondary ASI |
|:-------|:------------|:--------------|
| Data Leakage | ASI06, ASI07 | ASI01, ASI03 |
| Prompt Injection | ASI01, ASI06 | ASI09 |
| Tool Abuse | ASI02, ASI05 | ASI03 |
| Supply Chain | ASI04 | ASI10 |

## Review Workflow

### 1. Collect Findings
```
Aggregate results from:
- data_leakage_scan
- (future: prompt_injection_scan, tool_abuse_scan, etc.)
```

### 2. Apply Classification
```
For each finding:
1. Map to primary ASI category
2. Assign severity (Critical/High/Medium)
3. Validate exploitability
```

### 3. Filter & Dedupe
```
Remove:
- Test/demo code false positives
- Duplicate findings
- Low severity (not reported)
```

### 4. Generate Report
```
Use system prompt: agent_security_report.md
Output format: XML <vuln> blocks
```

## Severity Criteria

### Critical
- RCE capability (ASI05)
- Full agent control (ASI01, ASI10)
- Credential theft with exfiltration path

### High
- Data leakage with network exposure (ASI06, ASI07)
- Privilege escalation (ASI03)
- Tool exploitation with impact (ASI02)

### Medium
- Limited scope vulnerabilities
- Requires specific conditions
- Indirect attack paths

### Low (Not Reported)
- Code quality issues
- No exploitation path
- Local-only impact

## Integration

### Input
```json
{
  "scan_results": [
    {"module": "data_leakage", "findings": [...]}
  ]
}
```

### Output
```xml
<report>
  <vuln>
    <title>...</title>
    <risk_type>ASI06: Memory & Context Poisoning</risk_type>
    <level>High</level>
    ...
  </vuln>
</report>
```

## Related Resources

- **Skill**: `agent-security-review` - Review methodology
- **System Prompt**: `agent_security_report.md` - Report format
- **Reference**: OWASP Top 10 for Agentic Applications 2026
