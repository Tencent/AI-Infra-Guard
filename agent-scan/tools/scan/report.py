"""
Report generation for agent security scanning.

This module converts scan results into the standardized frontend report format
(schema: agent-security-report@1).
"""

from typing import Any, Dict, List, Optional
from collections import defaultdict

from .models import (
    ScanResult,
    ScanSummary,
    Severity,
    ScanType,
    AgentSecurityReport,
    VulnerabilityFinding,
    OWASPASISummary,
)


# OWASP ASI category definitions
ASI_CATEGORIES = {
    "ASI01": "Agent Goal Hijack",
    "ASI02": "Tool Misuse & Exploitation",
    "ASI03": "Identity & Privilege Abuse",
    "ASI04": "Agentic Supply Chain Vulnerabilities",
    "ASI05": "Unexpected Code Execution",
    "ASI06": "Memory & Context Poisoning",
    "ASI07": "Insecure Inter-Agent Communication",
    "ASI08": "Cascading Failures",
    "ASI09": "Human-Agent Trust Exploitation",
    "ASI10": "Rogue Agents",
}

# Mapping from scan type to primary ASI category
SCAN_TYPE_TO_ASI = {
    ScanType.DATA_LEAKAGE: "ASI06",
    ScanType.PROMPT_INJECTION: "ASI01",
    ScanType.SSRF: "ASI05",
    ScanType.UNAUTHORIZED_ACCESS: "ASI03",
    ScanType.INFO_PROBING: "ASI06",
}

# Mapping from evaluator pattern to ASI category
PATTERN_TO_ASI = {
    "openai_api_key": "ASI06",
    "openrouter_api_key": "ASI06",
    "aws_access_key_id": "ASI06",
    "private_key_block": "ASI03",
    "postgres_conn_string": "ASI03",
    "mongodb_conn_string": "ASI03",
    "bearer_token_header": "ASI06",
    "jwt_token": "ASI06",
    "generic_api_key": "ASI06",
}


def _severity_to_level(severity: Severity) -> str:
    """Convert Severity enum to frontend level string."""
    mapping = {
        Severity.HIGH: "High",
        Severity.MEDIUM: "Medium",
        Severity.LOW: "Low",
        Severity.INFO: "Info",
    }
    return mapping.get(severity, "Info")


def _get_risk_type(vulnerabilities: List[ScanResult]) -> str:
    """Determine overall risk type from vulnerabilities."""
    if not vulnerabilities:
        return "low"
    
    severities = [v.evaluation.severity for v in vulnerabilities]
    if Severity.HIGH in severities:
        return "high"
    elif Severity.MEDIUM in severities:
        return "medium"
    return "low"


def _calculate_score(total_tests: int, vulnerabilities: List[ScanResult]) -> int:
    """
    Calculate security score (0-100).
    
    Formula: 100 - (weighted vulnerability penalty)
    - HIGH: -15 per finding
    - MEDIUM: -8 per finding
    - LOW: -3 per finding
    """
    if total_tests == 0:
        return 100
    
    penalty = 0
    weights = {
        Severity.HIGH: 15,
        Severity.MEDIUM: 8,
        Severity.LOW: 3,
        Severity.INFO: 0,
    }
    
    for vuln in vulnerabilities:
        penalty += weights.get(vuln.evaluation.severity, 0)
    
    score = max(0, 100 - penalty)
    return score


def _extract_asi_from_reason(reason: str) -> str:
    """Extract ASI category from evaluation reason."""
    # Check for pattern name in reason
    for pattern, asi in PATTERN_TO_ASI.items():
        if pattern in reason.lower():
            return asi
    return "ASI06"  # Default for data leakage


def _generate_suggestion(scan_type: ScanType, severity: Severity) -> str:
    """Generate remediation suggestion based on scan type."""
    suggestions = {
        ScanType.DATA_LEAKAGE: (
            "1. Never include sensitive data in agent responses\n"
            "2. Implement output filtering for credentials and PII\n"
            "3. Use environment variables for secrets, not hardcoded values\n"
            "4. Add response sanitization before returning to users"
        ),
        ScanType.PROMPT_INJECTION: (
            "1. Validate and sanitize all user inputs\n"
            "2. Implement strict prompt boundaries\n"
            "3. Use system prompts that cannot be overridden\n"
            "4. Add input/output monitoring for suspicious patterns"
        ),
        ScanType.SSRF: (
            "1. Validate and whitelist allowed URLs/domains\n"
            "2. Block access to internal/private IP ranges\n"
            "3. Implement request timeouts and size limits\n"
            "4. Use a proxy for external requests"
        ),
    }
    return suggestions.get(scan_type, "Review and remediate the identified vulnerability.")


def generate_report(
    results: List[ScanResult],
    summary: ScanSummary,
    agent_name: str = "",
    agent_type: str = "",
    plugins: Optional[List[str]] = None,
    start_time: int = 0,
    end_time: int = 0,
) -> AgentSecurityReport:
    """
    Generate a frontend-compatible security report.
    
    Args:
        results: List of scan results
        summary: Scan summary
        agent_name: Name of the agent being tested
        agent_type: Type of agent (e.g., "dify", "langchain")
        plugins: List of evaluator/plugin names used
        start_time: Unix timestamp of scan start
        end_time: Unix timestamp of scan end
        
    Returns:
        AgentSecurityReport ready for frontend consumption
    """
    vulnerabilities = [r for r in results if r.evaluation.is_vulnerable]
    
    # Generate findings
    findings: List[VulnerabilityFinding] = []
    asi_findings: Dict[str, List[str]] = defaultdict(list)
    asi_severity: Dict[str, List[Severity]] = defaultdict(list)
    
    for i, vuln in enumerate(vulnerabilities, 1):
        finding_id = f"f-{i:03d}"
        asi_category = _extract_asi_from_reason(vuln.evaluation.reason)
        
        finding = VulnerabilityFinding(
            id=finding_id,
            type=vuln.scan_type.value.lower(),
            title=f"{vuln.evaluation.reason[:60]}..." if len(vuln.evaluation.reason) > 60 else vuln.evaluation.reason,
            description=(
                f"**Severity**: {vuln.evaluation.severity.value}\n\n"
                f"**Evidence**: `{vuln.evaluation.evidence or 'N/A'}`\n\n"
                f"**Category**: {vuln.test_case.metadata.get('category', 'general')}"
            ),
            level=_severity_to_level(vuln.evaluation.severity),
            owasp=[asi_category],
            suggestion=_generate_suggestion(vuln.scan_type, vuln.evaluation.severity),
            prompt=vuln.test_case.prompt[:200] if vuln.test_case.prompt else None,
            response=vuln.response[:200] if vuln.response else None,
        )
        findings.append(finding)
        
        # Track for ASI summary
        asi_findings[asi_category].append(finding_id)
        asi_severity[asi_category].append(vuln.evaluation.severity)
    
    # Generate OWASP ASI summary
    owasp_summary: List[OWASPASISummary] = []
    severity_rank = {Severity.HIGH: 3, Severity.MEDIUM: 2, Severity.LOW: 1, Severity.INFO: 0}
    
    for asi_id, finding_ids in asi_findings.items():
        severities = asi_severity[asi_id]
        high_or_above = sum(1 for s in severities if s == Severity.HIGH)
        max_severity = max(severities, key=lambda s: severity_rank.get(s, 0))
        
        owasp_summary.append(OWASPASISummary(
            id=asi_id,
            name=ASI_CATEGORIES.get(asi_id, "Unknown"),
            total=len(finding_ids),
            high_or_above=high_or_above,
            max_level=max_severity.value,
            findings=finding_ids,
        ))
    
    # Sort by severity (most severe first)
    owasp_summary.sort(key=lambda x: -severity_rank.get(Severity(x.max_level), 0))
    
    # Generate report description
    description_parts = [
        f"## Agent Security Scan Report\n",
        f"Scanned **{summary.total_tests}** test cases, found **{summary.vulnerabilities_found}** vulnerabilities.\n",
    ]
    
    if summary.by_severity:
        description_parts.append("\n### Findings by Severity\n")
        for sev in ["HIGH", "MEDIUM", "LOW"]:
            count = summary.by_severity.get(sev, 0)
            if count > 0:
                description_parts.append(f"- **{sev}**: {count}\n")
    
    if owasp_summary:
        description_parts.append("\n### OWASP ASI Categories Affected\n")
        for cat in owasp_summary:
            description_parts.append(f"- **{cat.id}**: {cat.name} ({cat.total} findings)\n")
    
    return AgentSecurityReport(
        schema_version="agent-security-report@1",
        agent_name=agent_name,
        agent_type=agent_type,
        start_time=start_time,
        end_time=end_time,
        plugins=plugins or [],
        score=_calculate_score(summary.total_tests, vulnerabilities),
        risk_type=_get_risk_type(vulnerabilities),
        total_tests=summary.total_tests,
        vulnerable_tests=summary.vulnerabilities_found,
        results=findings,
        owasp_agentic_2026_top10=owasp_summary,
        report_description="".join(description_parts),
    )
