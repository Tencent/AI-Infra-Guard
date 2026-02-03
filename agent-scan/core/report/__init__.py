"""
Security report generation for agent scanning pipeline.

Provides models and report generation (XML -> agent-security-report@1).
"""

from .report import generate_report_from_xml, calculate_security_score
from .models import (
    Severity,
    AgentSecurityReport,
    VulnerabilityFinding,
    OWASPASISummary,
    ConversationTurn,
)

__all__ = [
    "generate_report_from_xml",
    "calculate_security_score",
    "Severity",
    "AgentSecurityReport",
    "VulnerabilityFinding",
    "OWASPASISummary",
    "ConversationTurn",
]
