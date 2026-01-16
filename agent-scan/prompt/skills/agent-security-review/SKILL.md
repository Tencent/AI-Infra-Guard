# Agent Security Review Skill

**Version:** 1.0.0  
**Category:** Security Analysis  
**Standard:** OWASP Top 10 for Agentic Applications 2026

## Overview

This skill enables systematic review and classification of security findings from agent-based application scans. It applies the OWASP ASI (Agentic Security Issues) framework for standardized risk categorization.

## OWASP ASI Classification Reference

| ID | Risk Type | Key Indicators |
|:---|:----------|:---------------|
| ASI01 | Agent Goal Hijack | Prompt injection, instruction override |
| ASI02 | Tool Misuse & Exploitation | Unvalidated tool parameters, unauthorized calls |
| ASI03 | Identity & Privilege Abuse | Missing auth, privilege escalation |
| ASI04 | Agentic Supply Chain | Malicious packages, compromised tools |
| ASI05 | Unexpected Code Execution | RCE, eval(), command injection |
| ASI06 | Memory & Context Poisoning | Context leakage, memory manipulation |
| ASI07 | Insecure Inter-Agent Comm | Unencrypted channels, data exposure |
| ASI08 | Cascading Failures | Error propagation, chain reactions |
| ASI09 | Human-Agent Trust Exploit | Deceptive responses, social engineering |
| ASI10 | Rogue Agents | Malicious behavior, backdoors |

## Classification Guidelines

### Data Leakage → ASI Mapping

| Finding Type | Primary ASI | Rationale |
|:-------------|:------------|:----------|
| API key exposure | ASI06 | Context contains sensitive data |
| System prompt leak | ASI01 | Enables goal hijacking |
| Credential disclosure | ASI03 | Identity abuse risk |
| PII exposure | ASI07 | Inter-agent data leak |
| Config leakage | ASI04 | Supply chain info exposure |

### Severity Assignment

```
HIGH:   RCE, agent control, credential leak, data exfiltration
MEDIUM: Limited scope, requires conditions  
LOW:    Minor issues, no immediate risk
```

## Review Checklist

### Must Verify
- [ ] Exploitability confirmed
- [ ] Network reachability validated
- [ ] Not test/demo code
- [ ] Real security impact

### Must Filter
- [ ] Development artifacts
- [ ] Placeholder data
- [ ] Local-only issues
- [ ] Code quality (non-security)

## Report Format

```xml
<vuln>
  <title>Brief vulnerability summary</title>
  <desc>
  ## Technical Details
  **Location**: file:line
  **Type**: Description
  
  ### Attack Path
  Step-by-step exploitation
  
  ### Impact
  Security consequences
  </desc>
  <risk_type>ASI0X: Category Name</risk_type>
  <level>High|Medium|Low</level>
  <suggestion>Remediation steps</suggestion>
</vuln>
```

## Integration

This skill works with:
- `data-leakage-detection` - Detects sensitive data exposure
- `data-leakage-llm-evaluator` - Semantic analysis
- Future: `prompt-injection-detection`, `tool-abuse-detection`

## Related

- **Agent**: `agent-security-reviewer`
- **System Prompt**: `agent_security_report.md`
