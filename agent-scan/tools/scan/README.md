# Security Report Generation

Models and report generation for AI agent security scanning.

## Architecture

```
tools/scan/
├── models.py    # Data models (Severity, VulnerabilityFinding, AgentSecurityReport)
└── report.py    # Report generation (generate_report_from_xml)
```

## Usage

### Generate Report from XML

```python
from tools.scan import generate_report_from_xml

vuln_xml = """
<vuln>
  <title>API Key Disclosure</title>
  <desc>Agent leaked OpenAI API key in response</desc>
  <risk_type>ASI06: Memory & Context Poisoning</risk_type>
  <level>High</level>
  <suggestion>Implement output filtering</suggestion>
</vuln>
"""

report = generate_report_from_xml(
    vuln_text=vuln_xml,
    agent_name="my-agent",
    agent_type="dify",
)

print(report.dict())
```

### Models

| Model | Description |
|-------|-------------|
| `Severity` | HIGH, MEDIUM, LOW, INFO |
| `VulnerabilityFinding` | Single finding for frontend display |
| `AgentSecurityReport` | Complete report (schema: agent-security-report@1) |
| `OWASPASISummary` | OWASP ASI category summary |
| `ConversationTurn` | Prompt/response pair for evidence |

## Data Leakage Detection

Data leakage detection uses a **skill-based approach**:

- **Skill**: `prompt/skills/data-leakage-detection/SKILL.md`
- **Agent**: `prompt/agents/data_leakage_detection.md`

The agent uses `dialogue()` for interactive testing, with the skill providing attack vectors and evaluation criteria.
