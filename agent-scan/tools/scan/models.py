"""
Core data models for security report generation.

This module defines the data structures used for generating frontend-compatible
security reports (schema: agent-security-report@1).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class Severity(str, Enum):
    """Severity levels for security findings."""
    
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


# ============================================================================
# Frontend Report Models (schema: agent-security-report@1)
# ============================================================================

class ConversationTurn(BaseModel):
    """Single turn in a conversation for vulnerability evidence."""
    
    prompt: Optional[str] = None
    response: Optional[str] = None


class VulnerabilityFinding(BaseModel):
    """Single vulnerability finding for frontend display."""
    
    id: str
    type: str  # e.g., "data_leakage", "prompt_injection"
    title: str
    description: str  # Markdown supported
    level: str  # "High", "Medium", "Low"
    owasp: List[str] = Field(default_factory=list)  # e.g., ["ASI06"]
    suggestion: str  # Markdown supported
    conversation: List[ConversationTurn] = Field(default_factory=list)


class OWASPASISummary(BaseModel):
    """OWASP ASI category summary for frontend display."""
    
    id: str  # e.g., "ASI06"
    name: str  # e.g., "Memory & Context Poisoning"
    total: int
    high_or_above: int
    max_level: str  # "HIGH", "MEDIUM", "LOW"
    findings: List[str] = Field(default_factory=list)


class AgentSecurityReport(BaseModel):
    """
    Final security report format for frontend integration.
    
    Schema version: agent-security-report@1
    """
    
    schema_version: str = "agent-security-report@1"
    agent_name: str = ""
    agent_type: str = ""  # e.g., "dify", "langchain", "custom"
    model_name: str = ""  # e.g., "openai/gpt-4"
    start_time: int  # Unix timestamp
    end_time: int  # Unix timestamp
    plugins: List[str] = Field(default_factory=list)
    score: int = 100  # Security score (0-100)
    risk_type: str = "low"  # "high", "medium", "low"
    total_tests: int = 0
    vulnerable_tests: int = 0
    results: List[VulnerabilityFinding] = Field(default_factory=list)
    owasp_agentic_2026_top10: List[OWASPASISummary] = Field(default_factory=list)
    report_description: str = ""
