"""
Security report generation module.

Provides models and report generation for AI agent security scanning.
Data leakage detection is now skill-based (see prompt/skills/data-leakage-detection/).
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
