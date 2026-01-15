"""
Core data models for security scanning.

This module defines the fundamental data structures used across all security
scanning operations, including test cases, evaluation results, and scan results.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class Severity(str, Enum):
    """Severity levels for security findings."""
    
    CRITICAL = "CRITICAL"
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
