"""
Security report generation module.

Provides models and report generation for AI agent security scanning.
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
