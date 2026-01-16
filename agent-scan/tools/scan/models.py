"""
Core data models for security scanning.

This module defines the fundamental data structures used across all security
scanning operations, including test cases, evaluation results, and scan results.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class Severity(str, Enum):
    """Severity levels for security findings (High/Medium/Low)."""
    
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ScanType(str, Enum):
    """Types of security scans supported by the framework."""
    
    DATA_LEAKAGE = "DATA_LEAKAGE"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    INFO_PROBING = "INFO_PROBING"
    SSRF = "SSRF"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"


class ASICategory(str, Enum):
    """
    OWASP Top 10 for Agentic Applications 2026.
    
    Reference: https://owasp.org/www-project-top-10-for-agentic-applications/
    """
    
    ASI01 = "ASI01: Agent Goal Hijack"
    ASI02 = "ASI02: Tool Misuse & Exploitation"
    ASI03 = "ASI03: Identity & Privilege Abuse"
    ASI04 = "ASI04: Agentic Supply Chain Vulnerabilities"
    ASI05 = "ASI05: Unexpected Code Execution"
    ASI06 = "ASI06: Memory & Context Poisoning"
    ASI07 = "ASI07: Insecure Inter-Agent Communication"
    ASI08 = "ASI08: Cascading Failures"
    ASI09 = "ASI09: Human-Agent Trust Exploitation"
    ASI10 = "ASI10: Rogue Agents"


class TestCase(BaseModel):
    """
    Represents a single test case to be executed against an agent.
    
    Attributes:
        id: Unique identifier for the test case
        prompt: The input prompt/query to send to the agent
        metadata: Additional metadata about the test case (e.g., strategy, category)
        expected_result: Optional expected behavior or result
    """
    
    id: str
    prompt: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    expected_result: Optional[str] = None


class EvaluationResult(BaseModel):
    """
    Result of evaluating a single response.
    
    Attributes:
        is_vulnerable: Whether the response indicates a vulnerability
        severity: Severity level of the finding
        score: Confidence score (0.0 to 1.0)
        reason: Human-readable explanation of the finding
        evidence: Optional extracted evidence from the response
    """
    
    is_vulnerable: bool
    severity: Severity
    score: float = 0.0  # 0.0 to 1.0
    reason: str
    evidence: Optional[str] = None


class ScanResult(BaseModel):
    """
    Final result of a scan for a specific test case.
    
    Attributes:
        test_case: The test case that was executed
        response: The agent's response to the test case
        evaluation: Evaluation of the response
        scan_type: Type of scan performed
        timestamp: Unix timestamp when the scan was executed
        metadata: Additional metadata about the scan execution
    """
    
    test_case: TestCase
    response: str
    evaluation: EvaluationResult
    scan_type: ScanType
    timestamp: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScanSummary(BaseModel):
    """
    Summary of a complete scan session.
    
    Attributes:
        total_tests: Total number of test cases executed
        vulnerabilities_found: Number of vulnerabilities detected
        by_severity: Count of findings by severity level
        scan_type: Type of scan performed
        duration: Total scan duration in seconds
    """
    
    total_tests: int
    vulnerabilities_found: int
    by_severity: Dict[str, int] = Field(default_factory=dict)
    scan_type: ScanType
    duration: float


# ============================================================================
# Frontend Report Models (schema: agent-security-report@1)
# ============================================================================

class VulnerabilityFinding(BaseModel):
    """Single vulnerability finding for frontend display."""
    
    id: str
    type: str  # e.g., "data_leakage", "prompt_injection"
    title: str
    description: str  # Markdown supported
    level: str  # "High", "Medium", "Low"
    owasp: List[str] = Field(default_factory=list)  # e.g., ["ASI06"]
    suggestion: str  # Markdown supported
    prompt: Optional[str] = None
    response: Optional[str] = None


class OWASPASISummary(BaseModel):
    """OWASP ASI category summary for frontend display."""
    
    id: str  # e.g., "ASI06"
    name: str  # e.g., "Memory & Context Poisoning"
    total: int
    high_or_above: int
    max_level: str  # "HIGH", "MEDIUM", "LOW"
    findings: List[str] = Field(default_factory=list)  # Finding IDs


class AgentSecurityReport(BaseModel):
    """
    Final security report format for frontend integration.
    
    Schema version: agent-security-report@1
    """
    
    schema_version: str = "agent-security-report@1"
    agent_name: str = ""
    agent_type: str = ""  # e.g., "dify", "langchain", "custom"
    start_time: int  # Unix timestamp
    end_time: int  # Unix timestamp
    plugins: List[str] = Field(default_factory=list)  # Detection strategies used
    score: int = 100  # Security score (0-100)
    risk_type: str = "low"  # "high", "medium", "low"
    total_tests: int = 0
    vulnerable_tests: int = 0
    results: List[VulnerabilityFinding] = Field(default_factory=list)
    owasp_agentic_2026_top10: List[OWASPASISummary] = Field(default_factory=list)
    report_description: str = ""
